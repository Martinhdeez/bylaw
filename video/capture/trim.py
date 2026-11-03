"""Cut the raw 1920x1080 webm captures into the slots of the cut (H.264, 30 fps, 1x, no audio).
Usage: python3 trim.py <video dir> [probe]"""
import subprocess
import sys
from pathlib import Path

V = Path(sys.argv[1])
RAW, OUT = V / "out/raw", V / "out/captures"
OUT.mkdir(parents=True, exist_ok=True)
dur = lambda f: float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))
if "probe" in sys.argv:
    for f in sorted(RAW.glob("C*.webm")):
        print(f.name, dur(f))
    sys.exit()

enc = ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "16", "-r", "30", "-an", "-movflags", "+faststart"]
# name, raw, start (None = end - slot), slot
CUTS = [("C1-d1-guard-off", "C1", 0.0, 30), ("C2-d1-guard-on", "C2", None, 28),
        ("C3-d4-guard-on", "C3", None, 6.667), ("C4-d2-guard-on", "C4", None, 6.667), ("C5-legit-guard-on", "C5", None, 6.666),
        # C6, live: the customer types turn 2 and sends it; jump cut over the wait; the answer lands with the block
        ("C6a-live-d1-typing", "C6", 18.5, 7), ("C6b-live-d1-block", "C6", 48.7, 10)]
for name, raw, ss, slot in CUTS:
    src = RAW / f"{raw}.webm"
    L = dur(src)
    if ss is None:
        ss = max(0.0, L - slot)
    pad = max(0.0, slot - (L - ss))  # hold the last frame when the capture is shorter than the slot
    vf = "fps=30" + (f",tpad=stop_mode=clone:stop_duration={pad:.3f}" if pad else "")
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", str(src), "-t", f"{slot:.3f}", "-vf", vf, *enc,
                    str(OUT / f"{name}.mp4")], check=True)
    print(f"{name}: {raw}.webm {L:.2f} s, from {ss:.2f} s, slot {slot} s, held {pad:.2f} s")
