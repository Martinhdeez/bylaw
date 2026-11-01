"""Words per beat in video/script.md. Usage: python3 video/wordcount.py [--closed]

Counts the quoted lines (> ...) under each "## B<n>" heading. B8 has two versions;
the open one is counted unless --closed is given. Also checks the beat durations sum to 203 s (v2).
"""
import re
import sys
from pathlib import Path

text = (Path(__file__).parent / "script.md").read_text()
want = "B8-closed" if "--closed" in sys.argv else "B8-open"
beats = re.split(r"^## ", text, flags=re.M)[1:]
total_w = total_s = 0
for b in beats:
    head, body = b.split("\n", 1)
    bid = head.split(" ")[0]
    secs = int(re.search(r"(\d+) s$", head.strip()).group(1))
    if bid == "B8":
        body = body.split(f"**{want} (")[1].split("**B8-")[0]
    words = sum(len(l[1:].replace("/", " ").split()) for l in body.splitlines() if l.startswith(">"))
    total_w += words
    total_s += secs
    print(f"{bid:3} {secs:3d} s {words:3d} words {words / secs:.2f} w/s")
print(f"total {total_s} s {total_w} words {total_w / total_s * 60:.0f} wpm")
assert total_s == 203, total_s

# The teleprompter carries a copy of the script; it must match word for word.
tp = (Path(__file__).parent / "teleprompter.html").read_text()
tp_lines = re.findall(r'(?:"B\d+", "[^"]+", \d+, |open: |closed: )"([^"]+)"', tp)
md_lines = [l[2:] for l in text.splitlines() if l.startswith("> ")]
assert tp_lines == md_lines, "teleprompter.html and script.md differ"
print("teleprompter matches script.md")
