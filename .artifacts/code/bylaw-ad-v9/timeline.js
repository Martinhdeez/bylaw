      window.__timelines = window.__timelines || {};
      const master = gsap.timeline({ paused: true });
      const tl = gsap.timeline();
      const P = (l, f) => V[l][0] + f * V[l][1];
      const S0 = (id) => SC[id][0];
      const slam = (sel, t, from = 1.6) => tl.fromTo(sel, { opacity: 0, scale: from }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" }, t);
      const rise = (sel, t, d = 0.45) => tl.fromTo(sel, { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: d, ease: "power3.out" }, t);
      const fade = (sel, t, d = 0.35) => tl.fromTo(sel, { opacity: 0 }, { opacity: 1, duration: d }, t);
      const shake = (t, amp = 18) => tl.fromTo("#root", { x: amp, y: -amp / 2 }, { x: 0, y: 0, duration: 0.4, ease: "elastic.out(1, 0.25)" }, t);
      const punch = (sel, t) => tl.fromTo(sel, { scale: 1.12 }, { scale: 1, duration: 0.5, ease: "power3.out" }, t);
      const count = (id, to, t, d, fmt = (v) => Math.round(v).toLocaleString("en-US")) => {
        const o = { v: 0 };
        tl.fromTo(o, { v: 0 }, { v: to, duration: d, ease: "power2.out", onUpdate: () => { document.getElementById(id).textContent = fmt(o.v); } }, t);
      };
      const pop = (sel, t) => tl.fromTo(sel, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2.4)" }, t);

      // progress bar
      [1, 2, 3].forEach((n) => {
        const [a, b] = SECT[n];
        tl.set("#bl" + n, { color: "#3c475e" }, 0);
        tl.set("#bl" + n, { color: "#f4f6f9" }, a);
        tl.fromTo("#bf" + n, { scaleX: 0 }, { scaleX: 1, duration: b - a, ease: "none" }, a);
        if (n < 3) tl.set("#bl" + n, { color: "#7d889b" }, b);
      });

      // section cards
      ["c1", "c2", "c3"].forEach((c) => {
        const t = S0(c);
        tl.fromTo("#" + c + "x .n", { opacity: 0, scale: 2.2 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power4.in" }, t);
        rise("#" + c + "x .l", t + 0.2, 0.35);
        shake(t + 0.3, 16);
      });

      // P1 agents at work
      tl.set(["#p1a", "#p1b", "#p1c", "#p1t", "#p1u"], { opacity: 0 }, S0("P1"));
      tl.fromTo("#p1ring", { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.5, ease: "back.out(1.8)" }, S0("P1"));
      tl.fromTo("#p1ring", { boxShadow: "0 0 60px rgba(91,140,255,0.1)" }, { boxShadow: "0 0 160px rgba(91,140,255,0.45)", duration: 0.8, yoyo: true, repeat: 3 }, S0("P1") + 0.3);
      fade("#p1u", P("s1", 0.15));
      rise("#p1t", P("s1", 0.05));
      [["#p1a", 0.5], ["#p1b", 0.65], ["#p1c", 0.82]].forEach(([s, f]) => { pop(s, P("s1", f)); shake(P("s1", f) + 0.03, 8); });

      // P2 policy, then the hole
      tl.set(["#p2hole", "#p2t"], { opacity: 0 }, S0("P2"));
      tl.fromTo("#P2 > div:not(.paper)", { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.4, stagger: 0.1 }, S0("P2"));
      tl.fromTo("#p2doc", { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, S0("P2") + 0.15);
      tl.fromTo("#p2doc p", { opacity: 0, x: 30 }, { opacity: 1, x: 0, duration: 0.25, stagger: 0.25 }, P("s2", 0.5));
      tl.fromTo("#p2hole", { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, V["s3"][0] + 0.1);
      shake(V["s3"][0] + 0.12, 26);
      slam("#p2t", V["s3"][0] + 0.2, 1.4);

      // P4 ticket: upgrade, change flight, downgrade, changed
      tl.set(["#ok1", "#ok2", "#ok3", "#p4flash"], { opacity: 0 }, S0("P4"));
      tl.fromTo("#pass1", { opacity: 0, y: 80 }, { opacity: 1, y: 0, duration: 0.45, ease: "power3.out" }, S0("P4"));
      tl.fromTo("#pbadge", { scale: 1 }, { scale: 1.12, duration: 0.18, yoyo: true, repeat: 3 }, P("s4a", 0.45));
      slam("#ok1", P("s4b", 0.0), 2.2);
      tl.set("#pbadge", { textContent: "ECONOMY · CHANGES OK", color: "#12a06e", borderColor: "#12a06e" }, P("s4b", 0.05));
      punch("#pass1", P("s4b", 0.05));
      slam("#ok2", P("s4b", 0.38), 2.2);
      tl.to("#pass1", { x: -60, duration: 0.12, yoyo: true, repeat: 1 }, P("s4b", 0.4));
      tl.set("#pdate", { textContent: "OCT 29", backgroundColor: "#ff4d2e", color: "#fff", padding: "0 10px", borderRadius: "6px" }, P("s4b", 0.45));
      slam("#ok3", P("s4b", 0.72), 2.2);
      tl.set("#pbadge", { textContent: "BASIC ECONOMY · NO CHANGES", color: "#ff4d2e", borderColor: "#ff4d2e" }, P("s4b", 0.76));
      punch("#pass1", P("s4b", 0.76));
      tl.fromTo("#pdate", { scale: 1 }, { scale: 1.3, duration: 0.15, yoyo: true, repeat: 3 }, P("s4b", 0.85));
      tl.fromTo("#p4flash", { opacity: 0 }, { opacity: 1, duration: 0.08 }, V["s4c"][0]);
      slam("#p4flash p", V["s4c"][0], 2.2);
      shake(V["s4c"][0] + 0.05, 30);

      // P5 shooter clears the suspects, then the verdict and a zoom through the hole
      tl.set(["#pv1", "#pv2", "#P5 .x", "#P5 .ok"], { opacity: 0 }, S0("P5"));
      fade("#hud", S0("P5") + 0.05, 0.2);
      tl.fromTo("#nos .tgt", { opacity: 0, y: 60 }, { opacity: 1, y: 0, duration: 0.3, stagger: 0.08, ease: "back.out(2)" }, S0("P5"));
      tl.fromTo("#xhair", { opacity: 0, x: 860, y: 900 }, { opacity: 1, x: 520, y: 175, duration: 0.25, ease: "power3.out" }, S0("P5") + 0.1);
      [[1, 0.02, 520], [2, 0.3, 860], [3, 0.55, 1200]].forEach(([n, f, x], i) => {
        const t = P("s5a", f) + 0.25, sel = "#no" + n;
        if (i) tl.to("#xhair", { x, duration: 0.2, ease: "power3.inOut" }, t - 0.22);
        tl.fromTo("#xhair", { scale: 0.7 }, { scale: 1, duration: 0.18 }, t);
        tl.fromTo(sel + " .x", { opacity: 0, scale: 2 }, { opacity: 1, scale: 1, duration: 0.16, ease: "back.out(2)" }, t);
        tl.set(sel + " .ok", { opacity: 1 }, t);
        tl.to(sel + " .ic", { opacity: 0.3, rotation: (i - 1) * 12, duration: 0.2 }, t);
        tl.set("#hudn", { textContent: String(n) }, t);
        shake(t, 14);
      });
      tl.to("#xhair", { opacity: 0, scale: 2, duration: 0.2 }, P("s5a", 0.75));
      rise("#pv1", P("s5a", 0.68), 0.35);
      tl.fromTo("#pv1 .ic", { scale: 0, rotation: -20 }, { scale: 1, rotation: 0, duration: 0.3, ease: "back.out(3)" }, P("s5a", 0.72));
      tl.to(["#nos", "#pv1", "#hud"], { opacity: 0.2, duration: 0.25 }, V["s5b"][0] - 0.05);
      slam("#pv2", V["s5b"][0], 1.5);
      shake(V["s5b"][0] + 0.05, 20);
      tl.fromTo("#holeO", { scale: 0 }, { scale: 1, duration: 0.25, ease: "back.out(3)" }, V["s5b"][0] + 0.25);
      tl.to("#holeO", { scale: 80, duration: 0.5, ease: "power3.in" }, SC["P5"][1] - 0.5);

      // P6 guardrails watch the agent, nobody watches the policy
      tl.set(["#mkR", "#mkHole", "#p6t"], { opacity: 0 }, S0("P6"));
      tl.fromTo("#mkL", { opacity: 0, x: -80 }, { opacity: 1, x: 0, duration: 0.4, ease: "power3.out" }, S0("P6") + 0.05);
      tl.fromTo("#mkR", { opacity: 0, x: 80 }, { opacity: 1, x: 0, duration: 0.4, ease: "power3.out" }, P("s6", 0.4));
      tl.fromTo("#mkHole", { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, P("s6", 0.6));
      rise("#p6t", P("s6", 0.7));

      // P7 what each hole costs
      tl.set(["#p7a", "#p7b", "#p7c"], { opacity: 0 }, S0("P7"));
      fade("#P7 .colh", S0("P7"));
      [["#p7a", 0.25], ["#p7b", 0.5], ["#p7c", 0.75]].forEach(([s, f]) => { pop(s, P("s7", f)); shake(P("s7", f) + 0.05, 10); });
      count("p7n", 48200, P("s7", 0.25), 2.2, (v) => "−$" + Math.round(v).toLocaleString("en-US"));
      tl.fromTo("#P7 .tile3", { boxShadow: "0 0 0 rgba(255,77,46,0)" }, { boxShadow: "0 0 70px rgba(255,77,46,0.35)", duration: 0.5, yoyo: true, repeat: 1, stagger: 0.25 }, P("s7", 0.85));

      // Q1 logo builds while it cracks
      const q = S0("Q1");
      tl.set(["#ringE", "#wordE", "#q1t"], { opacity: 0 }, q);
      tl.fromTo("#revE", { attr: { r: 0 } }, { attr: { r: 170 }, duration: 0.8, ease: "none" }, q + 0.05);
      tl.fromTo("#crackE", { attr: { "stroke-dashoffset": 1 } }, { attr: { "stroke-dashoffset": 0 }, duration: 0.8, ease: "none" }, q + 0.07);
      [0.2, 0.4, 0.6].forEach((d, i) => tl.fromTo("#markE", { x: i % 2 ? -6 : 6, y: 4 }, { x: 0, y: 0, duration: 0.12 }, q + d));
      tl.fromTo("#ringE", { opacity: 0, scale: 0, transformOrigin: "65px 72.6px" }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, q + 0.85);
      shake(q + 0.85, 24);
      tl.fromTo("#wordE", { opacity: 0, x: -60 }, { opacity: 1, x: 0, duration: 0.45, ease: "power3.out" }, q + 0.95);
      rise("#q1t", P("s8", 0.35));

      // Q2 what goes in, what comes out, with data flowing through Bylaw
      tl.set(["#qi1", "#qi2", "#qc", "#qo1", "#qo2", "#qo3", ".flow"], { opacity: 0 }, S0("Q2"));
      fade("#Q2 .colh", S0("Q2"));
      tl.fromTo("#qi1", { opacity: 0, x: -80 }, { opacity: 1, x: 0, duration: 0.35, ease: "back.out(1.6)" }, P("s9", 0.4));
      tl.fromTo("#qi2", { opacity: 0, x: -80 }, { opacity: 1, x: 0, duration: 0.35, ease: "back.out(1.6)" }, P("s9", 0.8));
      slam("#qc", P("s9", 0.92), 1.6);
      shake(P("s9", 0.95), 14);
      ["#fl0", "#fl1"].forEach((d, i) => tl.fromTo(d, { opacity: 1, x: 0 }, { opacity: 0, x: 200, duration: 0.55, ease: "power1.in", repeat: 6, repeatDelay: 0.1 }, P("s9", 0.95) + i * 0.3));
      [["#qo1", "#fl2", 0.25], ["#qo2", "#fl3", 0.55], ["#qo3", "#fl4", 0.82]].forEach(([s, d, f]) => {
        tl.fromTo(d, { opacity: 1, x: -40 }, { opacity: 0, x: 140, duration: 0.4, ease: "power1.in", repeat: 2 }, P("s10", f) - 0.4);
        tl.fromTo(s, { opacity: 0, x: 80 }, { opacity: 1, x: 0, duration: 0.35, ease: "back.out(1.6)" }, P("s10", f));
      });

      // Q3 human approves, enforced live
      tl.set(["#q3sh", "#q3t"], { opacity: 0 }, S0("Q3"));
      tl.fromTo("#Q3 > div", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.4, stagger: 0.15 }, S0("Q3"));
      tl.fromTo("#q3btn", { scale: 1 }, { scale: 0.9, duration: 0.1, yoyo: true, repeat: 1 }, P("s11", 0.25));
      tl.to("#q3btn", { backgroundColor: "#f4f6f9", duration: 0.15 }, P("s11", 0.3));
      pop("#q3sh", P("s11", 0.55));
      rise("#q3t", P("s11", 0.7));

      // H1 reads
      rise("#H1 .cap", S0("H1"));
      tl.set("#h1r .rulec", { opacity: 0 }, S0("H1"));
      tl.fromTo("#h1doc", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.4 }, S0("H1") + 0.1);
      tl.fromTo("#h1r .rulec", { opacity: 0, x: 60 }, { opacity: 1, x: 0, duration: 0.25, stagger: 0.3, ease: "power3.out" }, P("s12", 0.5));

      // H2 searches
      rise("#H2 .cap", S0("H2"));
      fade("#graph", S0("H2") + 0.05);
      tl.to("#hot", { attr: { "stroke-dashoffset": 0 }, duration: V["s13"][1] * 0.55, ease: "power2.inOut" }, P("s13", 0.3));
      tl.fromTo("#goal", { scale: 1, transformOrigin: "780px 665px" }, { scale: 1.12, duration: 0.18, yoyo: true, repeat: 5 }, P("s13", 0.85));

      // H3 proves
      rise("#H3 .cap", S0("H3"));
      tl.set(["#stampH"], { opacity: 0 }, S0("H3"));
      tl.fromTo("#H3 .term > *", { opacity: 0, x: 40 }, { opacity: 1, x: 0, duration: 0.25, stagger: 0.3, ease: "power3.out" }, S0("H3") + 0.1);
      fade("#H3 .runs", P("s14", 0.45), 0.2);
      [1, 2, 3, 4, 5].forEach((i) => tl.fromTo("#run" + i, { background: "rgba(43,227,160,0)", borderColor: "#232c40", textContent: "" }, { background: "#2be3a0", borderColor: "#2be3a0", textContent: "✓", duration: 0.1 }, P("s14", 0.55) + (i - 1) * 0.3));
      slam("#stampH", P("s14", 0.55) + 1.6, 2.2);
      shake(P("s14", 0.55) + 1.65, 16);

      // H4 patches
      rise("#H4 .cap", S0("H4"));
      tl.set(["#fixp", "#plus", "#H4 .met"], { opacity: 0 }, S0("H4"));
      fade("#H4 .diff", S0("H4") + 0.05, 0.3);
      tl.fromTo("#holeD", { scale: 0 }, { scale: 1, duration: 0.25, ease: "back.out(3)" }, S0("H4") + 0.3);
      tl.fromTo("#plus", { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: 0.35 }, P("s15", 0.2));
      tl.fromTo("#fixp", { opacity: 0, scale: 2.4, rotation: 20 }, { opacity: 1, scale: 1, rotation: -8, duration: 0.25, ease: "back.out(2)" }, P("s15", 0.35));
      shake(P("s15", 0.37), 12);
      tl.fromTo("#crowd svg", { color: "#2e3a52" }, { color: "#2be3a0", duration: 0.06, stagger: 0.03 }, P("s15", 0.5));
      fade("#H4 .met", P("s15", 0.7), 0.3);
      count("replayed", 43, P("s15", 0.7), 1.0, (v) => Math.round(v) + "/43");
      punch("#blocked", P("s15", 0.9));

      // H5 enforces
      rise("#H5 .cap", S0("H5"));
      tl.set(["#rq1", "#rq2", "#blk"], { opacity: 0 }, S0("H5"));
      tl.fromTo("#H5 .node", { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.35, stagger: 0.12 }, S0("H5") + 0.1);
      tl.fromTo("#rq1", { opacity: 0, x: 0 }, { opacity: 1, x: 0, duration: 0.2 }, P("s16", 0.25));
      tl.to("#rq1", { x: 680, duration: 0.9, ease: "power1.inOut" }, P("s16", 0.3));
      tl.fromTo("#rq2", { opacity: 0, x: 0 }, { opacity: 1, x: 0, duration: 0.2 }, P("s16", 0.5));
      tl.to("#rq2", { x: 290, duration: 0.45, ease: "power2.in" }, P("s16", 0.55));
      tl.to("#rq2", { x: 250, opacity: 0.4, duration: 0.2 }, P("s16", 0.55) + 0.45);
      tl.fromTo("#pxy", { borderColor: "#2be3a0" }, { borderColor: "#ff4d2e", duration: 0.1, yoyo: true, repeat: 3 }, P("s16", 0.55) + 0.45);
      slam("#blk", P("s16", 0.7), 2);
      shake(P("s16", 0.7) + 0.05, 18);

      // H6 tested on tau2-bench: three holes
      tl.set(["#hh1", "#hh2", "#hh3"], { opacity: 0 }, S0("H6"));
      rise("#bench", S0("H6") + 0.05, 0.5);
      [1, 2, 3].forEach((n, i) => {
        const t = P("s17", 0.55) + i * 0.45;
        tl.fromTo("#hh" + n, { opacity: 0, scale: 1.8, rotation: -4 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.25, ease: "back.out(2.4)" }, t);
        tl.fromTo("#hh" + n + " .ic", { scale: 0 }, { scale: 1, duration: 0.25, ease: "back.out(3)" }, t + 0.1);
        shake(t, i === 2 ? 26 : 14);
      });

      // H7 open weights
      tl.set(["#k1", "#cloudX"], { opacity: 0 }, S0("H7"));
      tl.fromTo("#bldg", { opacity: 0, scale: 0.94 }, { opacity: 1, scale: 1, duration: 0.4 }, S0("H7") + 0.05);
      slam("#model", P("s18", 0.15), 1.4);
      tl.fromTo("#cloudX", { opacity: 0, x: 60 }, { opacity: 1, x: 0, duration: 0.3 }, P("s18", 0.5));
      rise("#k1", P("s18", 0.6));

      // E1 thesis
      [["#l1", 0.0], ["#l2", 0.33], ["#l3", 0.64]].forEach(([s, f]) => {
        slam(s, P("s19", f) + 0.05, 1.3);
        tl.fromTo(s + " .ic", { rotation: -40, scale: 0 }, { rotation: 0, scale: 1, duration: 0.3, ease: "back.out(3)" }, P("s19", f) + 0.1);
      });

      // E2 end card
      tl.set(["#m1", "#m2"], { opacity: 0 }, S0("E2"));
      tl.fromTo("#logoM", { opacity: 0, scale: 1.6 }, { opacity: 1, scale: 1, duration: 0.3, ease: "power4.in" }, S0("E2"));
      shake(S0("E2") + 0.3, 22);
      rise("#m1", P("s20", 0.3));
      fade("#m2", P("s20", 0.8), 0.5);

      master.add(tl, 0);
      window.__timelines["main"] = master;
      master.seek(0);
