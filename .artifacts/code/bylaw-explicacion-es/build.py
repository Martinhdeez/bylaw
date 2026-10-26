import json, subprocess, glob, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
LU = os.path.join(HERE, "..", "lucide")


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))


VD = {os.path.basename(p)[:-4]: round(dur(p), 2) for p in glob.glob("assets/vo/*.wav")}


def lucide(name, size, color, sw=1.5, style=""):
    t = open(os.path.join(LU, name + ".svg")).read()
    inner = " ".join(t[t.index(">", t.index("<svg")) + 1:t.rindex("</svg>")].split())
    return '<svg class="ic" width="%d" height="%d" viewBox="0 0 24 24" style="color: %s%s"><g fill="none" stroke="currentColor" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round">%s</g></svg>' % (size, size, color, style, sw, inner)


# ---- timeline: scenes are sequences of voice lines ----
SEQ = [
    ("card", "c1", 1, "El problema"),
    ("scene", "P1", ["s1"]), ("scene", "P2", ["s2", "s3"]), ("scene", "P4", ["s4a", "s4b", "s4c"]),
    ("scene", "P5", ["s5"]), ("scene", "P6", ["s6"]), ("scene", "P7", ["s7"]),
    ("card", "c2", 2, "Qué hace"),
    ("scene", "Q1", ["s8"]), ("scene", "Q2", ["s9", "s10"]), ("scene", "Q3", ["s11"]),
    ("card", "c3", 3, "Cómo lo hace"),
    ("scene", "H1", ["s12"]), ("scene", "H2", ["s13"]), ("scene", "H3", ["s14"]), ("scene", "H4", ["s15"]),
    ("scene", "H5", ["s16"]), ("scene", "H6", ["s17"]), ("scene", "H7", ["s18"]),
    ("scene", "E1", ["s19"]), ("scene", "E2", ["s20"]),
]
V, SC, SECT = {}, {}, {}
t, sect = 0.0, 0
for item in SEQ:
    if item[0] == "card":
        if sect: SECT[sect][1] = t
        sect = item[2]
        SECT[sect] = [t, None]
        SC[item[1]] = [round(t, 2), round(t + 1.5, 2)]
        t += 1.5
        continue
    _, sid, lines = item
    st = t
    t += 0.2
    for i, l in enumerate(lines):
        V[l] = [round(t, 2), VD[l]]
        t += VD[l] + (0.25 if i < len(lines) - 1 else 0)
    t += 0.35 if sid not in ("E2",) else 1.6
    SC[sid] = [round(st, 2), round(t, 2)]
SECT[3][1] = SC["H7"][1]
TOTAL = round(t, 2)

# ---- markup ----
css = open("base.css.html").read()
css = css.replace("</style>", """
      .bar { position: absolute; top: 34px; left: 50%; transform: translateX(-50%); display: flex; gap: 14px; z-index: 50; }
      .bar div { width: 270px; display: flex; flex-direction: column; gap: 10px; }
      .bar span { font: 700 19px var(--mono); letter-spacing: 0.14em; text-transform: uppercase; color: #3c475e; }
      .bar i { display: block; height: 5px; border-radius: 3px; background: #1a2131; overflow: hidden; }
      .bar i b { display: block; height: 100%; width: 100%; background: var(--red); transform-origin: left center; transform: scaleX(0); }
      .sec { display: flex; flex-direction: column; align-items: center; gap: 10px; }
      .sec .n { font: 900 260px/0.8 var(--display); font-stretch: 64%; color: var(--red); }
      .sec .l { font: 900 150px/0.9 var(--display); font-stretch: 64%; text-transform: uppercase; }
      .cap2 { position: absolute; left: 0; right: 0; bottom: 110px; text-align: center; font: 900 96px/0.95 var(--display); font-stretch: 64%; text-transform: uppercase; }
      .chipx { position: absolute; display: flex; align-items: center; gap: 18px; padding: 22px 30px; border-radius: 18px; background: var(--panel); border: 2px solid var(--line); font: 800 44px var(--display); font-stretch: 80%; }
      .ring { position: absolute; left: 50%; top: 43%; width: 330px; height: 330px; margin: -165px 0 0 -165px; border-radius: 50%; border: 3px solid rgba(91,140,255,0.4); display: grid; place-items: center; box-shadow: 0 0 120px rgba(91,140,255,0.2); }
      .paper { position: absolute; background: var(--paper); color: #0b0f17; border-radius: 20px; padding: 40px 46px; display: flex; flex-direction: column; gap: 18px; }
      .paper h4 { font: 700 22px var(--mono); color: #5b6576; }
      .paper p { font: 700 40px/1.2 var(--display); font-stretch: 85%; padding-left: 22px; border-left: 6px solid #c4cbd6; }
      .tile3 { width: 420px; height: 420px; border-radius: 26px; background: var(--panel); border: 2px solid var(--line); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 30px; text-align: center; padding: 30px; }
      .tile3 span { font: 900 54px/1 var(--display); font-stretch: 72%; text-transform: uppercase; }
      .io { position: absolute; width: 470px; padding: 26px 30px; border-radius: 20px; background: var(--panel); border: 2px solid var(--line); display: flex; align-items: center; gap: 22px; }
      .io b { font: 800 40px/1.05 var(--display); font-stretch: 80%; }
      .io small { display: block; font: 700 18px var(--mono); color: var(--muted); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 6px; }
      .colh { position: absolute; top: 170px; font: 700 26px var(--mono); letter-spacing: 0.2em; color: var(--muted); }
      .rulec { font: 500 27px var(--mono); padding: 16px 22px; border-radius: 10px; background: #0c111b; border: 2px solid var(--line); }
      .rulec b { font-weight: 700; margin-right: 18px; }
      .btn { font: 800 44px var(--display); font-stretch: 85%; padding: 22px 56px; border-radius: 16px; background: var(--green); color: #04130d; }
      .node { position: absolute; width: 280px; height: 220px; border-radius: 22px; background: var(--panel); border: 2px solid var(--line); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; font: 700 22px var(--mono); color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; }
      .req { position: absolute; font: 700 26px var(--mono); padding: 14px 22px; border-radius: 12px; white-space: nowrap; }
      .blk { position: absolute; font: 900 60px/1 var(--display); font-stretch: 80%; color: var(--red); border: 6px solid var(--red); border-radius: 12px; padding: 10px 22px; transform: rotate(-6deg); white-space: nowrap; }
    </style>""")

pass_html = lambda pid, date, hl, res: '<div id="%s" class="pass"><div class="main"><div class="route">MAD → BCN</div><div class="meta"><span><small>FECHA</small>%s</span><span><small>SALIDA</small>09:40</span><span><small>RES</small>%s</span></div><div class="badge">BÁSICO · SIN CAMBIOS</div></div><div class="stub"><div class="bars"></div></div></div>' % (pid, '<b class="hl">%s</b>' % date if hl else date, res)
holeO = '<span class="hole-o"></span>'
N3 = '<svg width="%d" height="%d" style="color: #f4f6f9"><use href="#N3" /></svg>'

S = {}
S["c1"] = S["c2"] = S["c3"] = None
S["P1"] = ('<div class="ring" id="p1ring">' + lucide("bot", 200, "#5b8cff", 1.3) + '</div>'
           + '<div class="chipx" id="p1a" style="left: 250px; top: 300px">' + lucide("plane", 54, "#5b8cff") + 'Cancela vuelos</div>'
           + '<div class="chipx" id="p1b" style="left: 1300px; top: 220px">' + lucide("banknote", 54, "#2be3a0") + 'Devuelve dinero</div>'
           + '<div class="chipx" id="p1c" style="left: 1320px; top: 560px">' + lucide("ticket", 54, "#f4f6f9") + 'Cambia reservas</div>'
           + '<p class="cap2" id="p1t">Agentes de IA atienden a tus clientes</p>')
S["P2"] = ('<div style="position: absolute; left: 230px; top: 330px">' + lucide("bot", 200, "#5b8cff", 1.3) + '</div>'
           + '<div style="position: absolute; left: 500px; top: 400px">' + lucide("arrow-right", 90, "#3c475e", 2) + '</div>'
           + '<div class="paper" id="p2doc" style="left: 660px; top: 170px; width: 1040px"><h4>política.md · normas de la empresa</h4><p>Un billete básico no se puede modificar.</p><p>No se puede añadir seguro tras reservar.</p><p>No se puede cambiar el número de pasajeros.</p><div id="p2hole" class="hole" style="width: 130px; height: 130px; right: -40px; top: -50px; box-shadow: 0 0 0 10px var(--red), 0 0 60px 16px rgba(255,77,46,0.6)"></div></div>'
           + '<p class="cap2" id="p2t" style="bottom: 90px">Las normas tienen <span class="red">agujeros.</span></p>')
S["P4"] = (pass_html("pass1", "28 OCT", False, "8XK2QF") + pass_html("pass2", "29 OCT", True, "9MV7TA")
           + '<div id="ok1" class="chip">✓ Cancelar</div><div id="ok2" class="chip">✓ Reservar</div>'
           + '<div id="p4flash" class="flash center"><p class="huge" style="font-size: 300px; color: #fff">Cambiado.</p></div>')
S["P5"] = ('<div class="center" style="position: absolute; inset: 0"><p id="p5a" class="huge" style="font-size: 110px; display: flex; align-items: center; gap: 30px">' + lucide("bot", 130, "#2be3a0", 1.4) + 'El agente no hizo nada mal.</p>'
           + '<p id="p5b" class="huge red" style="font-size: 140px; margin-top: 40px">El fallo está en la n<span id="p5o" class="hole-o"></span>rma.</p></div>')
S["P6"] = ('<div id="mkL" class="mk" style="left: 200px"><span class="lbl green">Guardarraíles</span>' + lucide("shield-check", 220, "#2be3a0", 1.3) + '<span class="lbl muted">vigilan al agente</span></div>'
           + '<div id="mkR" class="mk" style="right: 200px"><span class="lbl red">La política</span><div class="pol"><i></i><i style="width: 70%"></i><i></i><i style="width: 50%"></i><i></i><i style="width: 80%"></i><div id="mkHole" class="hole"></div></div><span class="lbl muted">no la revisa nadie</span></div>'
           + '<p id="p6t" class="huge mkline" style="top: 780px; text-align: center">Nadie revisa <span class="red">la ley.</span></p>')
S["P7"] = ('<p class="colh" style="left: 0; right: 0; text-align: center; top: 150px">CADA AGUJERO CUESTA</p><div style="position: absolute; left: 0; right: 0; top: 300px; display: flex; justify-content: center; gap: 50px">'
           + '<div class="tile3" id="p7a">' + lucide("banknote", 150, "#ff4d2e", 1.3) + '<span>Dinero perdido</span></div>'
           + '<div class="tile3" id="p7b">' + lucide("users", 150, "#ff4d2e", 1.3) + '<span>Clientes tratados injustamente</span></div>'
           + '<div class="tile3" id="p7c">' + lucide("gavel", 150, "#ff4d2e", 1.3) + '<span>Auditorías suspendidas</span></div></div>')
S["Q1"] = ('<div class="center" style="position: absolute; inset: 0"><div class="logo"><svg id="markE" width="260" height="260" viewBox="0 0 120 120"><rect x="8" y="8" width="104" height="104" rx="28" fill="#f4f6f9" mask="url(#mE)" /><circle id="ringE" cx="65" cy="72.6" r="7.6" fill="#07090e" stroke="#ff4d2e" stroke-width="5" /></svg><div id="wordE" class="word">bylaw</div></div>'
           + '<p id="q1t" class="huge" style="font-size: 92px; margin-top: 70px">El auditor de las normas <span class="red">de tus agentes.</span></p></div>')
S["Q2"] = ('<p class="colh" style="left: 150px">ENTRA</p><p class="colh" style="right: 330px">SALE</p>'
           + '<div class="io" id="qi1" style="left: 120px; top: 300px">' + lucide("bot", 80, "#5b8cff") + '<div><small>tu agente</small><b>Sus herramientas</b></div></div>'
           + '<div class="io" id="qi2" style="left: 120px; top: 560px">' + lucide("file-text", 80, "#f4f6f9") + '<div><small>tu política</small><b>Sus normas</b></div></div>'
           + '<div id="qc" style="position: absolute; left: 770px; top: 340px">' + N3 % (380, 380) + '</div>'
           + '<div id="qa1" style="position: absolute; left: 640px; top: 470px">' + lucide("arrow-right", 90, "#3c475e", 2) + '</div><div id="qa2" style="position: absolute; left: 1190px; top: 470px">' + lucide("arrow-right", 90, "#3c475e", 2) + '</div>'
           + '<div class="io" id="qo1" style="left: 1330px; top: 230px"><div class="hole" style="position: relative; flex: none; width: 70px; height: 70px; box-shadow: 0 0 0 7px var(--red), 0 0 40px 10px rgba(255,77,46,0.5)"></div><div><small>1 · demostrados</small><b>Los agujeros</b></div></div>'
           + '<div class="io" id="qo2" style="left: 1330px; top: 450px">' + lucide("wrench", 80, "#2be3a0") + '<div><small>2 · listos para aprobar</small><b>Los parches</b></div></div>'
           + '<div class="io" id="qo3" style="left: 1330px; top: 670px">' + lucide("scale", 80, "#f4f6f9") + '<div><small>3 · medido</small><b>Lo que cuesta cada parche</b></div></div>')
S["Q3"] = ('<div style="position: absolute; left: 0; right: 0; top: 230px; display: flex; justify-content: center; align-items: center; gap: 60px">' + lucide("user-check", 170, "#f4f6f9", 1.3) + '<div id="q3btn" class="btn">Aprobar parche</div></div>'
           + '<div style="position: absolute; left: 0; right: 0; top: 560px; display: flex; justify-content: center; align-items: center; gap: 50px">' + lucide("bot", 130, "#5b8cff", 1.3) + lucide("arrow-right", 70, "#3c475e", 2) + '<div id="q3sh">' + lucide("shield-check", 170, "#2be3a0", 1.3) + '</div>' + lucide("arrow-right", 70, "#3c475e", 2) + lucide("wrench", 130, "#7d889b", 1.3) + '</div>'
           + '<p class="cap2" id="q3t" style="bottom: 90px; font-size: 80px">Aplicado en <span class="green">tiempo real.</span></p>')


def cap(k, t, d, green=False):
    return '<div class="cap"><span class="k%s">%s</span><span class="t">%s</span><span class="d">%s</span></div>' % (" g" if green else "", k, t, d)


S["H1"] = (cap("Paso 1 · Muse Spark · 1M de contexto", "Lee", "La política entera, de una vez, convertida en reglas que se pueden comprobar.")
           + '<div class="stage"><div class="paper" id="h1doc" style="left: 0; right: 0; top: 0; padding: 30px 36px"><h4>política.md</h4><p style="font-size: 30px">Un billete básico no se puede modificar.</p><p style="font-size: 30px">El seguro no se puede añadir tras reservar.</p></div>'
           + '<div id="h1r" style="position: absolute; left: 0; right: 0; top: 330px; display: flex; flex-direction: column; gap: 16px">'
           + '<div class="rulec"><b class="red">PROHIBIDO</b>básico ∧ vuelos_cambiados</div><div class="rulec"><b class="red">PROHIBIDO</b>seguro_añadido_tras_reserva</div><div class="rulec"><b class="green">REGLA</b>cancelar ⇐ &lt;24h ∨ seguro ∨ business</div><div class="rulec"><b class="green">REGLA</b>pasajeros.n = constante</div></div></div>')
S["H2"] = (cap("Paso 2 · Muse Spark · razonamiento máximo", "Busca", "Cadenas de acciones permitidas que acaban en algo prohibido.")
           + '<div class="stage"><svg id="graph" viewBox="0 0 940 840"><g stroke="#232c40" stroke-width="4" fill="none"><path d="M160 140 L470 140" /><path d="M160 140 L160 420" /><path d="M160 420 L470 420" /><path d="M470 140 L780 420" /><path d="M470 420 L470 680" /><path d="M160 420 L470 680" /></g>'
           + '<path id="hot" d="M160 140 L470 140 L780 420 L780 650" stroke="#ff4d2e" stroke-width="10" fill="none" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" />'
           + '<g font-family="JetBrains Mono, monospace" font-size="22" text-anchor="middle" font-weight="700">'
           + "".join('<g><rect x="%d" y="%d" width="280" height="80" rx="12" fill="#111725" stroke="%s" stroke-width="3" /><text x="%d" y="%d" fill="%s">%s</text></g>' % (x - 140, y - 40, c, x, y + 8, tc, n) for x, y, n, c, tc in [(160, 140, "consultar_reserva", "#2be3a0", "#f4f6f9"), (470, 140, "cancelar ✓", "#2be3a0", "#f4f6f9"), (160, 420, "buscar_vuelos", "#232c40", "#7d889b"), (470, 420, "modificar", "#232c40", "#7d889b"), (780, 420, "reservar ✓", "#2be3a0", "#f4f6f9"), (470, 680, "certificado", "#232c40", "#7d889b")])
           + '<g id="goal"><rect x="640" y="620" width="280" height="90" rx="12" fill="#ff4d2e" /><text x="780" y="674" fill="#07090e" font-size="30" font-weight="800">PROHIBIDO</text></g></g></svg></div>')
S["H3"] = (cap("Paso 3 · simulador <span style=\"font-family: Georgia, serif\">τ</span>²-bench", "Demuestra", "Cada cadena se ejecuta de verdad. Si no se reproduce, no cuenta.", True)
           + '<div class="stage"><div class="term"><span class="h">AGUJERO #1 · CLASE A</span>'
           + '<div class="r"><span><span class="q">›</span> get_reservation_details("8XK2QF")</span><span class="q">básico</span></div>'
           + '<div class="r"><span><span class="q">›</span> cancel_reservation("8XK2QF")</span><b>✓ permitido</b></div>'
           + '<div class="r"><span><span class="q">›</span> book_reservation(MAD→BCN, 29 OCT)</span><b>✓ permitido</b></div>'
           + '<div class="r bad"><span>= billete básico cambiado</span><b>✗ prohibido</b></div></div>'
           + '<div class="runs">REPETICIONES ' + "".join('<i id="run%d"></i>' % i for i in range(1, 6)) + '</div>'
           + '<div id="stampH" class="stamp">Reproducido 5/5<small>TRAZA EJECUTADA · NO UNA OPINIÓN</small></div></div>')
S["H4"] = (cap("Paso 4 · Muse Spark redacta", "Parchea", "Cada enmienda se prueba contra todos los casos pasados.")
           + '<div class="stage"><div class="diff"><span class="f">política.md · enmienda 1</span><div id="holeD" class="holeD"></div><div id="fixp" class="fixp" style="font-size: 22px">ARREGLADO</div>'
           + '<p class="minus">Un billete básico no se puede modificar.</p><p id="plus" class="plus">+ Tampoco cancelando y reservando el mismo viaje.</p></div>'
           + '<div id="crowd" class="crowd">' + "".join(lucide("user", 30, "#2e3a52") for _ in range(50)) + '</div>'
           + '<div class="met"><div><b id="replayed">0/50</b><span>casos pasados repetidos</span></div><div><b id="blocked">0</b><span>clientes honestos bloqueados</span></div></div></div>')
S["H5"] = (cap("Paso 5 · un humano aprueba", "Hace cumplir", "Un proxy MCP delante de tu agente.")
           + '<div class="stage"><div class="node" style="left: 0; top: 260px">' + lucide("bot", 110, "#5b8cff", 1.3) + 'tu agente</div>'
           + '<div class="node" style="left: 330px; top: 260px; border-color: var(--green)">' + N3 % (110, 110) + 'proxy MCP</div>'
           + '<div class="node" style="left: 660px; top: 260px">' + lucide("wrench", 110, "#7d889b", 1.3) + 'herramientas</div>'
           + '<div id="rq1" class="req" style="left: 10px; top: 160px; background: rgba(43,227,160,0.15); color: var(--green)">cancelar ✓</div>'
           + '<div id="rq2" class="req" style="left: 10px; top: 540px; background: rgba(255,77,46,0.15); color: var(--red)">reservar mismo viaje</div>'
           + '<div id="blk" class="blk" style="left: 300px; top: 620px">BLOQUEADO</div></div>')
S["H6"] = ('<div class="center" style="position: absolute; inset: 0"><div id="bench" class="bench"><span class="sub">probado sobre el banco de pruebas de los grandes laboratorios</span><span class="logo2"><span style="font-family: Georgia, serif; font-weight: 700">τ</span>²-bench <span class="muted" style="font-size: 120px">airline</span></span></div>'
           + '<div style="display: flex; gap: 40px; margin-top: 60px; align-items: center">' + "".join('<div class="hole h6h" style="position: relative; width: 110px; height: 110px; box-shadow: 0 0 0 9px var(--red), 0 0 50px 14px rgba(255,77,46,0.55)"></div>' for _ in range(3)) + '<span class="huge red" style="font-size: 120px; margin-left: 30px">3 agujeros</span></div></div>')
S["H7"] = ('<div id="cloudX" style="position: absolute; left: 1690px; top: 300px">' + lucide("cloud-off", 200, "#ff4d2e", 1.3) + '</div><div id="bldg" class="bldg"><span class="lbl">tu infraestructura</span><div class="pol"><i></i><i style="width: 70%"></i><i></i><i style="width: 50%"></i><i></i></div><div id="model" class="model">Muse Spark Open<small>PESOS ABIERTOS</small></div>' + N3 % (200, 200) + '</div>'
           + '<p id="k1" class="huge" style="position: absolute; top: 720px; left: 0; right: 0; text-align: center; font-size: 104px">Tu política nunca <span class="green">sale de casa.</span></p>')
S["E1"] = ('<div class="center" style="position: absolute; inset: 0"><p id="l1" class="th" style="font-size: 120px">' + lucide("pen-line", 120, "#f4f6f9") + 'Muse escribe la ley.</p><p id="l2" class="th red" style="font-size: 120px">' + lucide("hammer", 120, "#ff4d2e") + 'Muse rompe la ley.</p><p id="l3" class="th green" style="font-size: 120px">' + lucide("shield-check", 120, "#2be3a0") + 'El código la hace cumplir.</p></div>')
S["E2"] = ('<div class="center" style="position: absolute; inset: 0"><div class="logo" id="logoM">' + N3 % (200, 200) + '<div class="word" style="font-size: 190px">bylaw</div></div>'
           + '<p id="m1" class="huge" style="font-size: 116px; margin-top: 60px">Encuentra los aguj' + holeO + 'ros <span class="red">antes.</span></p><p id="m2" class="built">Construido sobre <b>Muse Spark</b> · funciona con <b>Muse Spark Open</b></p></div>')

clips = []
for item in SEQ:
    sid = item[1]
    a, b = SC[sid]
    inner = S[sid] if item[0] == "scene" else '<div class="sec" id="%sx"><span class="n">%d</span><span class="l">%s</span></div>' % (sid, item[2], item[3])
    clips.append('      <div id="%s" class="clip%s" data-start="%s" data-duration="%s" data-track-index="0">%s</div>' % (sid, " center" if item[0] == "card" else "", a, round(b - a, 2), inner))
bar = '      <div id="bar" class="clip" data-start="0" data-duration="%s" data-track-index="1"><div class="bar">%s</div></div>' % (TOTAL, "".join('<div><span id="bl%d">%d · %s</span><i><b id="bf%d"></b></i></div>' % (n, n, l, n) for n, l in [(1, "El problema"), (2, "Qué hace"), (3, "Cómo lo hace")]))

# ---- audio ----
A = [("pad", 0, TOTAL, "pad", 0.17), ("arp", SC["Q1"][0] + 0.6, SC["E1"][0] - SC["Q1"][0] - 0.6, "arp", 0.22)]
for l, (st, d) in V.items():
    A.append(("vo-" + l, st, d, "vo/" + l, 1))
fx = lambda name, at, v=0.5, d=1.0: A.append(("fx%d" % len(A), round(at, 2), d, name, v))
for c in ("c1", "c2", "c3"):
    fx("whoosh", SC[c][0] - 0.3, 0.35, 1.2); fx("thud", SC[c][0] + 0.1, 0.4)
P = lambda l, f: round(V[l][0] + f * V[l][1], 2)
for f in (0.55, 0.7, 0.85): fx("pop", P("s1", f), 0.35, 0.6)
fx("boom", V["s3"][0] + 0.1, 0.5, 2)
fx("pop", P("s4b", 0.05), 0.35, 0.6); fx("pop", P("s4b", 0.55), 0.35, 0.6); fx("boom", V["s4c"][0], 0.55, 2)
fx("thud", P("s5", 0.55), 0.45)
for f in (0.15, 0.45, 0.75): fx("pop", P("s7", f), 0.35, 0.6)
fx("riser", SC["Q1"][0] - 1.0, 0.4, 1.7); fx("crackle", SC["Q1"][0] + 0.1, 0.5, 0.9); fx("boom", SC["Q1"][0] + 0.75, 0.5, 2)
for f in (0.3, 0.7): fx("pop", P("s9", f), 0.3, 0.6)
for f in (0.2, 0.5, 0.78): fx("pop", P("s10", f), 0.3, 0.6)
fx("thud", P("s11", 0.25), 0.45)
for i in range(5): fx("pop", P("s14", 0.55) + i * 0.3, 0.25, 0.6)
fx("thud", P("s14", 0.55) + 1.6, 0.45)
fx("thud", P("s15", 0.35), 0.4)
fx("boom", P("s16", 0.75), 0.45, 2)
for i in range(3): fx("pop", P("s17", 0.6) + i * 0.4, 0.35, 0.6)
fx("boom", SC["E2"][0] + 0.05, 0.55, 2)
audio = "\n".join('      <audio id="%s" data-start="%s" data-duration="%s" src="assets/%s.wav" data-volume="%s"></audio>' % (i, round(s, 2), round(d, 2), f, v) for i, s, d, f, v in A)

defs = """    <svg width="0" height="0" style="position: absolute" aria-hidden="true"><defs>
      <mask id="mN3" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120"><rect width="120" height="120" fill="#fff" /><g transform="translate(60 60) scale(0.84) translate(-60 -60)"><rect x="26" y="16" width="22" height="88" rx="5" fill="#000" /><rect x="38" y="46" width="56" height="58" rx="24" fill="#000" /></g><path d="M122.0 6.0 L109.3 12.7 L107.5 25.3 L92.0 33.6 L90.0 47.9 L73.5 57.3 L66.2 73.0 L52.3 76.6 L45.5 94.7 L31.0 101.9 L22.0 118.0" fill="none" stroke="#000" stroke-width="7" stroke-linejoin="round" /></mask>
      <symbol id="N3" viewBox="0 0 120 120"><rect x="8" y="8" width="104" height="104" rx="28" fill="currentColor" mask="url(#mN3)" /><circle cx="65.0" cy="72.6" r="7.6" fill="#07090E" stroke="#FF4D2E" stroke-width="5" /></symbol>
      <mask id="mE" maskUnits="userSpaceOnUse" x="0" y="0" width="120" height="120"><circle id="revE" cx="122" cy="6" r="0" fill="#fff" /><g transform="translate(60 60) scale(0.84) translate(-60 -60)"><rect x="26" y="16" width="22" height="88" rx="5" fill="#000" /><rect x="38" y="46" width="56" height="58" rx="24" fill="#000" /></g><path id="crackE" d="M122.0 6.0 L109.3 12.7 L107.5 25.3 L92.0 33.6 L90.0 47.9 L73.5 57.3 L66.2 73.0 L52.3 76.6 L45.5 94.7 L31.0 101.9 L22.0 118.0" fill="none" stroke="#000" stroke-width="7" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" /></mask>
    </defs></svg>"""

js = open("timeline.js").read()
html = """<!doctype html>
<html lang="es" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,500..900&family=JetBrains+Mono:wght@500;700&display=block" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    %s
  </head>
  <body>
%s
    <div id="root" data-composition-id="main" data-start="0" data-duration="%s" data-width="1920" data-height="1080">
%s
%s
%s
    </div>
    <script>
      const V = %s, SC = %s, SECT = %s;
%s
    </script>
  </body>
</html>
""" % (css.strip(), defs, TOTAL, "\n".join(clips), bar, audio, json.dumps(V), json.dumps(SC), json.dumps(SECT), js)
open("index.html", "w").write(html)
print("total", TOTAL, "scenes", len(SC))
