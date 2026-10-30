"""UI7 restyle text contrast, both themes, with soft washes composited over their base (worst case: full wash alpha).
Run: python3 web/scripts/contrast.py   Prints every pair and flags any text pair under 4.5:1 (3:1 for large text)."""


def rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def over(base, *washes):
    r, g, b = rgb(base)
    for (wr, wg, wb, a) in washes:
        r, g, b = r + (wr - r) * a, g + (wg - g) * a, b + (wb - b) * a
    return "#%02x%02x%02x" % (round(r), round(g), round(b))


def lum(h):
    c = [x / 255 for x in rgb(h)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def cr(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True); return (x + 0.05) / (y + 0.05)


T = {
    "dark": dict(ground="#0f1122", surface="#171a30", step="#1f2340", raise_="#292e52", ink="#f5f6ff", ink2="#dcdff2", muted="#b3b8d6", faint="#959bc0",
                 violet_hi="#c4a6ff", blue="#86b4ff", red="#ff6b5a", green="#34e0a1", amber="#ffb84d", coral="#ff8a7a", blk="#ff8a7a", amber_lbl="#ffb84d",
                 vsoft=(157, 107, 255, .16), bsoft=(110, 160, 255, .16), rsoft=(255, 107, 90, .15), gsoft=(52, 224, 161, .14), asoft=(255, 184, 77, .14),
                 msoft=(196, 166, 255, .10), vbtn="#7346f5", bbtn="#3157e0", rat_a="#34e0a1", rat_b="#22c3e6", rat_ink="#062a1d"),
    "light": dict(ground="#eef0fa", surface="#fafbff", step="#e8eaf6", raise_="#dcdff0", ink="#14162b", ink2="#2b2e48", muted="#4a4f6e", faint="#585d7c",
                  violet_hi="#5b22cf", blue="#1f5fd6", red="#c4300f", green="#08774e", amber="#965400", coral="#c4300f", blk="#a3260b", amber_lbl="#7a4400",
                  vsoft=(106, 46, 224, .09), bsoft=(31, 95, 214, .09), rsoft=(196, 48, 15, .09), gsoft=(8, 119, 78, .09), asoft=(201, 120, 0, .12),
                  msoft=(196, 166, 255, .10), vbtn="#6a2ee0", bbtn="#1f5fd6", rat_a="#08774e", rat_b="#0a6c8a", rat_ink="#ffffff"),
}

bad = 0
for name, t in T.items():
    s = t
    pairs = []
    for bg in ("ground", "surface", "step", "raise_"):
        for fg in ("ink", "ink2", "muted", "faint"):
            pairs.append((f"{fg} on {bg}", s[fg], s[bg], False))
    for fg in ("violet_hi", "blue", "red", "green", "amber", "coral"):
        pairs.append((f"{fg} on surface", s[fg], s["surface"], False))
        pairs.append((f"{fg} on step", s[fg], s["step"], False))
    # stat cards and metrics: label in the accent on its own wash
    for fg, w in (("violet_hi", "vsoft"), ("red", "rsoft"), ("amber", "asoft"), ("blue", "bsoft"), ("green", "gsoft")):
        pairs.append((f"stat label {fg} on surface+{w}", s[fg], over(s["surface"], s[w]), False))
        pairs.append((f"muted on surface+{w}", s["muted"], over(s["surface"], s[w]), False))
    # hero wash, nav current, selected domain, Muse tag
    pairs.append(("title ink on ground+violet+blue wash", s["ink"], over(s["ground"], s["vsoft"], s["bsoft"]), False))
    pairs.append(("lede muted on ground+violet+blue wash", s["muted"], over(s["ground"], s["vsoft"], s["bsoft"]), False))
    pairs.append(("nav current ink on surface+violet+blue", s["ink"], over(s["surface"], s["vsoft"], s["bsoft"]), False))
    pairs.append(("domain muted on step+violet", s["muted"], over(s["step"], s["vsoft"]), False))
    pairs.append(("Muse tag on surface+tint", s["violet_hi"], over(s["surface"], s["msoft"]), False))
    # Live: blocked pill on the blocked row (two red washes), decision line, result figures (large)
    pairs.append(("Live blocked pill on surface+row+pill red", s["blk"], over(s["surface"], s["rsoft"], s["rsoft"]), False))
    pairs.append(("Live dd.blk red on surface+green wash", s["red"], over(s["surface"], s["gsoft"]), False))
    pairs.append(("Live muted on result before wash", s["muted"], over(s["surface"], s["rsoft"]), False))
    pairs.append(("Live muted on result after wash", s["muted"], over(s["surface"], s["gsoft"]), False))
    for fg, w in (("red", "rsoft"), ("amber", "rsoft"), ("green", "gsoft"), ("blue", "gsoft")):
        pairs.append((f"result figure {fg} (large) on surface+{w}", s[fg], over(s["surface"], s[w]), True))
    pairs.append(("Live allowed green on surface", s["green"], s["surface"], False))
    # Amendment: trade-off label, ratified stamp, enforced panel
    pairs.append(("trade-off label on step+amber", s["amber_lbl"], over(s["step"], s["asoft"]), False))
    pairs.append(("trade-off ink on step+amber", s["ink"], over(s["step"], s["asoft"]), False))
    pairs.append(("stamp green (large) on surface+green", s["green"], over(s["surface"], s["gsoft"]), True))
    pairs.append(("stamp date green on surface+green", s["green"], over(s["surface"], s["gsoft"]), False))
    pairs.append(("enforced muted on surface+green", s["muted"], over(s["surface"], s["gsoft"]), False))
    # buttons
    for bgk in ("vbtn", "bbtn"):
        pairs.append((f"white on {bgk}", "#ffffff", s[bgk], False))
    for bgk in ("rat_a", "rat_b"):
        pairs.append((f"ratify text on {bgk}", s["rat_ink"], s[bgk], False))
    print(f"== {name}")
    for label, fg, bg, large in pairs:
        r = cr(fg, bg); need = 3.0 if large else 4.5
        flag = "" if r >= need else "   <-- FAIL"
        bad += bool(flag)
        print(f"  {r:5.2f}  {label}{flag}")
print("failures:", bad)
