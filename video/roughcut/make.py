"""Writes video/roughcut/index.html: the v2 cut, silent, no subtitles, no labels.

Beats and planned durations come from video/script.md. Generated beats are the MP4s cut by
`video/build.sh beats`; app beats are the VZ3 placeholders, or the real captures (C1-C5) when they are
in roughcut/assets/. Every app beat carries a traceability HUD drawn from video/figures.json
(written by video/figures.py from committed files): model, Muse usage, estimated cost, event file,
commit, rule and policy, replay and backtest where they apply, recording time.

With a recorded voice (--final --timing FILE from video/align.py), beat slots follow the voice and
generated beats play 0.8-1.25x to fit; the audio itself is mixed by build.sh.

v3: B4 carries a 6 s slot for the user's own Ratify click (C8, to record; the A6 store frame until then),
and B5b is the live D1 session typed into the UI on Muse (C6, two segments with a jump cut over the wait).

Usage: python3 video/roughcut/make.py [--final --timing FILE]
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
FIG = json.loads((HERE.parent / "figures.json").read_text())
argv = sys.argv[1:]
final = "--final" in argv
timing = json.loads(Path(argv[argv.index("--timing") + 1]).read_text()) if "--timing" in argv else None

# beat -> [(generated or placeholder asset, final capture or None, seconds, HUD run key or None)]
MEDIA = {
    "B0": [("B0-opening.mp4", None, 7, None)],
    "B1": [("B1-guard-off.mp4", "C1-d1-guard-off.mp4", 30, "d1_off")],
    "B2": [("B2-what-happened.mp4", None, 12, None)],
    "B3": [("B3-thesis.mp4", None, 14, None)],
    "B4": [("B4-how-a.mp4", None, 25, None), ("BR-user-ratifies-fallback.mp4", "C8-user-ratifies.mp4", 6, None),
           ("B4-how-b.mp4", None, 5, None)],
    "B5": [("B5-guard-on.mp4", "C2-d1-guard-on.mp4", 28, "d1_on")],
    "B5b": [("C6a-live-d1-typing.mp4", "C6a-live-d1-typing.mp4", 7, "live_d1"),
            ("C6b-live-d1-block.mp4", "C6b-live-d1-block.mp4", 10, "live_d1")],
    "B6": [("B6-0-d4.mp4", "C3-d4-guard-on.mp4", 6.667, "d4_on"), ("B6-1-d2.mp4", "C4-d2-guard-on.mp4", 6.667, "d2_on"),
           ("B6-2-legit.mp4", "C5-legit-guard-on.mp4", 6.666, "legit_on")],
    "B7": [("B7-generality.mp4", None, 16, None)],
    "B8": [("B8-measured.mp4", None, 18, None)],
    "B9": [("B9-trace.mp4", None, 20, None)],
    "B10": [("B10-close.mp4", None, 8, None)],
}
TITLE = {"d1_off": "Vouchers on an on-time flight, guard off", "d1_on": "Vouchers on an on-time flight, guard on",
         "d4_on": "Compensation after a cancel, guard on", "d2_on": "Someone else's seat, guard on",
         "legit_on": "A real missed connection, guard on", "live_d1": "Live on Muse, guard on"}

beats = []
for part in re.split(r"^## ", (HERE.parent / "script.md").read_text(), flags=re.M)[1:]:
    head = part.split("\n", 1)[0]
    bid, title, span, dur = [x.strip() for x in head.split("·")]
    beats.append({"id": bid, "planned": int(dur.split()[0])})
assert [b["id"] for b in beats] == list(MEDIA), "script.md beats and MEDIA differ"

t = 0.0
for i, b in enumerate(beats):
    if timing:
        tb = timing["beats"][i]
        assert tb["id"] == b["id"]
        b["start"], b["dur"] = tb["start"], tb["duration"]
    else:
        b["start"], b["dur"] = t, b["planned"]
    t = b["start"] + b["dur"]
total = t

e = html.escape
n = lambda x: f"{x:,}"
P = FIG["price"]


def hud(key, hid, start, dur):
    r = FIG["runs"][key]
    c, u = r["check"], r["usage"]
    if c["allowed"]:
        verdict, cls = "allowed", "ok"
    elif c["enforced"]:
        verdict, cls = "denied", "deny"
    else:
        verdict, cls = "would deny; guard off, so it ran", "warn"
    rows = [
        ("Event file", f'<span class="code">{e(r["file"])}</span>'),
        ("Recorded", e(r["started"][:19].replace("T", " ")) + " UTC"),
        ("Model", f'<span class="code">{e(r["model"])}</span>'),
        ("Wall clock", f'{r["wall_s"]:.1f} s' + ('<span class="sub">The cut skips 23.2 s of waiting.</span>' if key == "live_d1" else "")),
        ("Muse usage", (f'{u["calls"]} calls, {n(u["input"])} in, {n(u["output"])} out' if u["calls"] else f'{n(u["tokens"])} tokens')
         + f'<span class="sub">{e(u["scope"])}</span>'),
        ("Est. cost", (f'${u["cost"]:.2f}' + ("" if u["scope"] == "this run" else " for the batch")) if "cost" in u
         else f'${u["cost_lo"]:.2f} to ${u["cost_hi"]:.2f}, all input to all output'),
        ("Committed in", f'<span class="code">{e(r["commit"])}</span>'),
        (f'Check at {c["t_check"]:.3f} s', f'<span class="code">{e(c["tool"])}</span> <span class="{cls}">{e(verdict)}</span>'
         + (f'<span class="code rid">{e(c["rule_id"])}</span>' if c["rule_id"] else "")),
    ]
    if c["policy_ref"] and key != "live_d1":  # live: same rule and policy as B5, the space goes to usage
        rows.append(("Policy", e(c["policy_ref"].split(";")[0]) + "."))
    if "replay" in r:
        rows.append(("Replay, backtest", f'{e(r["replay"])} reached the goal, {e(r["backtest"])} honest blocked'))
    body = "".join(f'<div class="k">{k}</div><div class="v">{v}</div>' for k, v in rows)
    return (f'      <div id="{hid}" class="clip hud" data-start="{start:.3f}" data-duration="{dur:.3f}" data-track-index="2">'
            f'<div class="h">{e(TITLE[key])}</div>{body}'
            f'<div class="price">Cost at ${P["input"]} input, ${P["output"]} output per 1M tokens, {e(P["url"].replace("https://", ""))}</div></div>')


clips, huds, missing = [], [], []
for b in beats:
    scale = b["dur"] / b["planned"]
    m = b["start"]
    for ph, cap, secs, key in MEDIA[b["id"]]:
        use = cap if cap and (HERE / "assets" / cap).exists() else ph
        if final and cap and not (HERE / "assets" / cap).exists():
            missing.append(cap)
        slot = secs * scale
        rate = ""
        if not key:
            rate = f' data-playback-rate="{min(1.25, max(0.8, 1 / scale)):.4f}"' if timing else ""
        vid = "v-" + use.split(".")[0].lower()
        cls = "media app" if key else "media"
        clips.append(f'      <video id="{vid}" class="clip {cls}" src="assets/{use}" muted playsinline data-start="{m:.3f}" data-duration="{slot:.3f}" data-track-index="1"{rate}></video>')
        if key:
            huds.append(hud(key, "hud-" + use.split(".")[0].lower(), m, slot))
        m += slot

page = f"""<!doctype html>
<html lang="en" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      @font-face {{ font-family: "Fira Sans"; font-weight: 400; src: url("assets/fonts/fira-sans-latin-400-normal.woff2") format("woff2"); }}
      @font-face {{ font-family: "Fira Sans"; font-weight: 500; src: url("assets/fonts/fira-sans-latin-500-normal.woff2") format("woff2"); }}
      @font-face {{ font-family: "Fira Sans"; font-weight: 600; src: url("assets/fonts/fira-sans-latin-600-normal.woff2") format("woff2"); }}
      @font-face {{ font-family: "Fira Code"; font-weight: 500; src: url("assets/fonts/fira-code-latin-500-normal.woff2") format("woff2"); }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #0f1122; }}
      #root {{ position: relative; width: 100%; height: 100%; background: #0f1122; font-variant-numeric: tabular-nums; font-variant-ligatures: none; font-feature-settings: "calt" 0, "liga" 0; }}
      .media {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; object-fit: contain; }}
      /* app beats: the app on the left, the HUD in a column on the right */
      .media.app {{ width: 1500px; }}
      .hud {{ position: absolute; left: 1520px; top: 40px; width: 372px; bottom: 40px; padding-left: 22px; border-left: 1px solid rgba(220,223,242,.22);
        font: 400 21px/1.3 "Fira Sans"; color: #f5f6ff; }}
      .hud .h {{ font: 600 27px/1.2 "Fira Sans"; margin-bottom: 14px; }}
      .hud .k {{ font: 400 18px/1.2 "Fira Sans"; color: #959bc0; margin-top: 12px; }}
      .hud .v {{ margin-top: 3px; overflow-wrap: anywhere; }}
      .hud .code {{ font: 500 19px/1.3 "Fira Code"; color: #dcdff2; }}
      .hud .rid {{ display: block; margin-top: 3px; }}
      .hud .sub {{ display: block; font-size: 18px; color: #b3b8d6; }}
      .hud .ok {{ color: #34e0a1; font-weight: 500; }} .hud .deny {{ color: #ff6b5a; font-weight: 500; }} .hud .warn {{ color: #ffb84d; font-weight: 500; }}
      .hud .price {{ position: absolute; left: 22px; right: 0; bottom: 0; font: 400 16px/1.3 "Fira Sans"; color: #959bc0; }}
    </style>
  </head>
  <body>
    <!-- generated by video/roughcut/make.py ({'final' if final else 'rough cut'}, silent); do not edit by hand -->
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="1920" data-height="1080">
{chr(10).join(clips)}
{chr(10).join(huds)}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
(HERE / "index.html").write_text(page)
print(f"wrote {HERE / 'index.html'}: {total:.2f} s, {len(huds)} HUDs, {'final' if final else 'rough cut'}, silent")
if missing:
    print("still placeholders (no capture in roughcut/assets):", ", ".join(missing))
