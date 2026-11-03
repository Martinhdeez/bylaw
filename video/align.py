"""Align Martín's voice to the script beats. Usage:
  python3 video/align.py video/out/voice/transcript.json [-o video/out/voice/timing.json]

Input: the word list from `npx hyperframes transcribe` ([{"text", "start", "end"}, ...]).
Output: per beat, where the voice starts and ends, and per subtitle chunk (the script's '/' pieces)
its start time, matched word by word with difflib so misheard words do not break it.
"""
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
args = [a for a in sys.argv[1:] if not a.startswith("-")]
out = Path(sys.argv[sys.argv.index("-o") + 1]) if "-o" in sys.argv else HERE / "out/voice/timing.json"
norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())

words = json.loads(Path(args[0]).read_text())
if isinstance(words, dict):
    words = words.get("words") or words.get("segments")
heard = [norm(w["text"]) for w in words]

script = (HERE / "script.md").read_text()
beats, tokens = [], []  # tokens: (word, beat index, chunk index)
for part in re.split(r"^## ", script, flags=re.M)[1:]:
    head, body = part.split("\n", 1)
    bid, title, span, dur = [x.strip() for x in head.split("·")]
    line = " ".join(l[1:].strip() for l in body.splitlines() if l.startswith(">"))
    chunks = [c.strip() for c in line.split("/") if c.strip()]
    for ci, c in enumerate(chunks):
        tokens += [(norm(w), len(beats), ci) for w in c.split() if norm(w)]
    beats.append({"id": bid, "title": title, "planned": int(dur.split()[0]), "chunks": chunks})

sm = difflib.SequenceMatcher(None, [t[0] for t in tokens], heard, autojunk=False)
when = {}  # script token index -> (start, end) in the voice
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        when[a + k] = (words[b + k]["start"], words[b + k]["end"])
print(f"matched {len(when)} of {len(tokens)} script words")

for bi, beat in enumerate(beats):
    idx = [i for i, t in enumerate(tokens) if t[1] == bi and i in when]
    assert idx, f"{beat['id']}: no words matched; check the take"
    beat["voice_start"] = when[idx[0]][0]
    beat["voice_end"] = when[idx[-1]][1]
    starts = []
    for ci in range(len(beat["chunks"])):
        hit = [when[i][0] for i, t in enumerate(tokens) if t[1] == bi and t[2] == ci and i in when]
        starts.append(hit[0] if hit else None)
    beat["chunk_starts"] = starts

# Picture slots: a beat runs from its voice start (first beat from 0) to the next beat's voice start;
# the last beat keeps 2.5 s after the last word for the end card.
for bi, beat in enumerate(beats):
    beat["start"] = 0.0 if bi == 0 else round(beat["voice_start"] - 0.25, 3)
for bi, beat in enumerate(beats):
    end = beats[bi + 1]["start"] if bi + 1 < len(beats) else beat["voice_end"] + 2.5
    beat["duration"] = round(end - beat["start"], 3)
    print(f"{beat['id']:3} planned {beat['planned']:3d} s  slot {beat['start']:7.2f} +{beat['duration']:6.2f} s  voice {beat['voice_end'] - beat['voice_start']:5.2f} s")
total = beats[-1]["start"] + beats[-1]["duration"]
print(f"total {total:.2f} s" + ("  OVER 180 s: trim pauses or re-record a beat" if total > 180 else ""))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"total": total, "beats": beats}, indent=1))
print(f"wrote {out}")
