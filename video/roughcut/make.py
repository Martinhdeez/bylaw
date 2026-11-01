"""Writes video/roughcut/index.html from video/script.md.

Rough cut (default): the planned beat times, placeholder app footage, a burned-in beat label per
beat, the script as subtitles timed evenly by word count, and the music bed.
Final picture (--final --timing video/out/voice/timing.json): beat slots and subtitle times from
the aligned voice (video/align.py), real captures where they exist in assets/, no labels and no
audio (the voice and the ducked bed are mixed by ffmpeg, see ASSEMBLY.md).

In the final picture, subtitles are burned only on the app-capture beats (generated beats already
carry their words on screen); --srt FILE writes every line as a caption sidecar for the upload.

Usage: python3 video/roughcut/make.py [--closed] [--final --timing FILE] [--no-subs] [--srt FILE]
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
argv = sys.argv[1:]
final = "--final" in argv
subs = "--no-subs" not in argv
timing = json.loads(Path(argv[argv.index("--timing") + 1]).read_text()) if "--timing" in argv else None
want = "B8-closed" if "--closed" in argv else "B8-open"
if timing:
    assert timing["version"] == want, f"timing was aligned for {timing['version']}, not {want}"

# beat -> planned media: [(placeholder or generated asset, final capture asset or None, seconds)], label kind
MEDIA = {
    "B1": ([("B1-hook.mp4", None, 12)], "generated"),
    "B2": ([("B2-thesis.mp4", None, 10)], "generated"),
    "B3": ([("B3-guard-off.mp4", "C1-d1-guard-off.mp4", 30)], "app capture"),
    "B4": ([("B4-how.mp4", None, 30)], "generated"),
    "B5": ([("B5-guard-on.mp4", "C2-d1-guard-on.mp4", 28)], "app capture"),
    "B6": ([("B6-0-d4.mp4", "C3-d4-guard-on.mp4", 6.667), ("B6-1-d2.mp4", "C4-d2-guard-on.mp4", 6.667),
            ("B6-2-legit.mp4", "C5-legit-guard-on.mp4", 6.666)], "app capture"),
    "B7": ([("B7-generality.mp4", None, 18)], "generated"),
    "B8": ([("B8-measured.mp4", None, 20)], "generated"),
    "B9": ([("B9-close.mp4", None, 12)], "generated"),
}

beats = []
for part in re.split(r"^## ", script := (HERE.parent / "script.md").read_text(), flags=re.M)[1:]:
    head, body = part.split("\n", 1)
    bid, title, span, dur = [x.strip() for x in head.split("·")]
    if bid == "B8":
        body = body.split(f"**{want} (")[1].split("**B8-")[0]
    line = " ".join(l[1:].strip() for l in body.splitlines() if l.startswith(">"))
    beats.append({"id": bid, "title": title, "span": span, "planned": int(dur.split()[0]),
                  "chunks": [c.strip() for c in line.split("/") if c.strip()]})

t = 0.0
for i, b in enumerate(beats):
    if timing:
        tb = timing["beats"][i]
        assert tb["id"] == b["id"]
        b["start"], b["dur"], b["chunk_starts"], b["voice_end"] = tb["start"], tb["duration"], tb["chunk_starts"], tb["voice_end"]
    else:
        b["start"], b["dur"], b["chunk_starts"], b["voice_end"] = t, b["planned"], None, t + b["planned"] - 0.25
    t = b["start"] + b["dur"]
total = t

clips, labels, caps, missing, srt = [], [], [], [], []
for b in beats:
    files, kind = MEDIA[b["id"]]
    scale = b["dur"] / b["planned"]  # slot vs planned: generated beats play slower or faster to fit
    m = b["start"]
    for ph, cap, secs in files:
        use = cap if cap and (HERE / "assets" / cap).exists() else ph
        if final and cap and use == ph:
            missing.append(cap)
        slot = secs * scale
        rate = ""
        if use == ph and kind == "generated":
            r = min(1.25, max(0.8, 1 / scale))
            rate = f' data-playback-rate="{r:.4f}"'
        vid = "v-" + use.split(".")[0].lower()
        clips.append(f'      <video id="{vid}" class="clip media" src="assets/{use}" muted playsinline data-start="{m:.3f}" data-duration="{slot:.3f}" data-track-index="1"{rate}></video>')
        m += slot
    if not final:
        tag = kind if kind == "generated" else kind + " · PLACEHOLDER: VZ3 prototype"
        labels.append(f'      <div id="lb-{b["id"].lower()}" class="clip label" data-start="{b["start"]:.3f}" data-duration="{b["dur"]:.3f}" data-track-index="2">'
                      f'{b["id"]} · {html.escape(b["title"])} · {b["span"]} · {html.escape(tag)}</div>')
    words = [len(c.split()) for c in b["chunks"]]
    starts = b["chunk_starts"]
    if not starts:
        c0, starts = b["start"] + 0.25, []
        for w in words:
            starts.append(c0)
            c0 += (b["dur"] - 0.5) * w / sum(words)
    for i, c in enumerate(b["chunks"]):
        s = starts[i] if starts[i] is not None else (starts[i - 1] or b["start"]) + 0.5
        e = next((x for x in starts[i + 1:] if x is not None), b["voice_end"] + 0.3)
        srt.append((s, s + max(0.4, e - s), c))
        if subs and not (final and kind == "generated"):
            caps.append(f'        <div id="cap-{b["id"].lower()}-{i}" class="clip cap" data-start="{s:.3f}" data-duration="{max(0.4, e - s):.3f}" data-track-index="4">{html.escape(c)}</div>')

audio = "" if final else '      <audio id="bed" class="clip" src="assets/bed.wav" data-start="0" data-duration="180" data-track-index="5" data-volume="0.35"></audio>'
page = f"""<!doctype html>
<html lang="en" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Fira Sans"; font-weight: 500; src: url("assets/fonts/fira-sans-latin-500-normal.woff2") format("woff2"); }}
      @font-face {{ font-family: "Fira Code"; font-weight: 500; src: url("assets/fonts/fira-code-latin-500-normal.woff2") format("woff2"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #0f1122; }}
      #root {{ position: relative; width: 100%; height: 100%; background: #0f1122; }}
      .media {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; object-fit: contain; }}
      .label {{ position: absolute; left: 24px; top: 20px; z-index: 5; padding: 8px 14px; border-radius: 4px; font: 500 22px/1 "Fira Code";
        color: #ffb84d; background: rgba(11,13,27,.86); border: 1px solid rgba(255,184,77,.5); }}
      #caps {{ position: absolute; left: 0; right: 0; bottom: 70px; height: 140px; z-index: 6; }}
      .cap {{ position: absolute; left: 50%; bottom: 0; transform: translateX(-50%); max-width: 1500px; width: max-content; text-align: center;
        padding: 14px 26px; border-radius: 6px; font: 500 44px/1.25 "Fira Sans"; color: #f5f6ff; background: rgba(11,13,27,.84); }}
    </style>
  </head>
  <body>
    <!-- generated by video/roughcut/make.py ({'final' if final else 'rough cut'}, {want}); do not edit by hand -->
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="1920" data-height="1080">
{chr(10).join(clips)}
{chr(10).join(labels)}
      <div id="caps" data-track-kind="captions" data-layout-allow-caption-zone>
{chr(10).join(caps)}
      </div>
{audio}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
(HERE / "index.html").write_text(page)
print(f"wrote {HERE / 'index.html'}: {total:.2f} s, {len(caps)} subtitles, {want}, {'final' if final else 'rough cut'}")
if "--srt" in argv:
    ts = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x % 1 * 1000)) % 1000:03d}"
    Path(argv[argv.index("--srt") + 1]).write_text("".join(f"{n}\n{ts(a)} --> {ts(b)}\n{c}\n\n" for n, (a, b, c) in enumerate(srt, 1)))
if missing:
    print("still placeholders (no capture in roughcut/assets):", ", ".join(missing))
