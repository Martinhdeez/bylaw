import { useRef, type PointerEvent } from "react";
import { Gauge } from "lucide-react";
import { api, useGet, type Bench as BenchT, type Domain } from "../api";
import { Crumbs, Failure, Loading, Muse, Ticker, int } from "../ui";

const LABEL = { muse: "Muse-guided", bfs: "Blind BFS" } as const;
const COLOR = { muse: "var(--violet-hi)", bfs: "var(--faint)", off: "var(--muted)" } as const;
const per1k = (holes: number, calls: number) => (calls ? (holes / calls) * 1000 : 0);

export function Bench({ domain }: { domain: Domain }) {
  const bench = useGet<BenchT>(api.bench(domain));
  const crumbs = <Crumbs items={[[`${domain} bench`]]} />;

  if (bench.loading) return <div className="page">{crumbs}<Loading what="the bench" shape="bench" /></div>;
  if (bench.error?.status === 404)
    return (
      <div className="page">
        {crumbs}
        <h1 className="title">No {domain} bench yet</h1>
        <section className="panel empty-state">
          <span className="shield"><Gauge aria-hidden="true" /></span>
          <p>The bench compares Muse-guided search with blind BFS on the same budget. Produce it with <code translate="no">uv run python -m bylaw bench --domain {domain} --budget 2000</code>.</p>
        </section>
      </div>
    );
  if (!bench.data) return <div className="page">{crumbs}<Failure error={bench.error!} onRetry={bench.reload} /></div>;

  const { rows, budget, model } = bench.data;
  // 01 v1.9: a null top-level model means no Muse call succeeded; a bench from before v1.9 has no model key.
  const asked = rows.some((r) => r.mode === "muse");
  const muse = model !== null ? rows.find((r) => r.mode === "muse") : undefined;
  const label = (m: Row["mode"]) => (m === "muse" && !muse ? "Muse unavailable" : LABEL[m]);
  // A Muse row without a model searched as blind BFS: never in the Muse accent.
  const color = (m: Row["mode"]) => (m === "muse" && !muse ? COLOR.off : COLOR[m]);
  const cls = (k: "contradictions" | "ambiguities") => rows.map((r) => `${label(r.mode)} ${r[k] ?? "unknown"}`).join(", ");
  const bfs = rows.find((r) => r.mode === "bfs");
  const maxHoles = Math.max(1, ...rows.map((r) => r.holes));
  const ratio = muse && bfs && per1k(bfs.holes, bfs.tool_calls) > 0 ? per1k(muse.holes, muse.tool_calls) / per1k(bfs.holes, bfs.tool_calls) : null;
  const onlyMuse = muse && bfs ? muse.hole_keys.filter((k) => !bfs.hole_keys.includes(k)) : [];
  const first = (r?: Row) => (r?.found?.length ? Math.min(...r.found.map((f) => f.tool_calls)) : null);
  const fm = first(muse), fb = first(bfs);

  return (
    <div className="page">
      {crumbs}
      <div className="head">
        <div>
          {muse ? (
            <>
              <h1 className="title"><span className="v">Muse-guided</span> search against blind BFS</h1>
              <p className="lede">Same {domain} policy, same budget of {int(budget)} tool calls, same depth limit, one run per mode. Muse Spark proposes chains per forbidden goal before BFS fills the rest of the budget.</p>
            </>
          ) : (
            <>
              <h1 className="title">Blind BFS search</h1>
              <p className="lede">
                The {domain} policy searched by blind BFS on a budget of {int(budget)} tool calls, one run per mode. {asked ? "Muse unavailable: the Muse run got no answer from Muse Spark, so it searched as blind BFS too." : "No Muse Spark in this bench."}
              </p>
            </>
          )}
        </div>
        {muse && <Muse>{model ? `Chains proposed by Muse Spark, ${model}` : "Chains proposed by Muse Spark"}</Muse>}
      </div>

      <div className="bench">
        <section className="panel">
          <div className="panel-h">
            <h2>Holes proven by tool calls spent <span className="label">log scale</span></h2>
            <div className="legend">{rows.map((r) => <span key={r.mode}><i style={{ background: color(r.mode) }} />{label(r.mode)}</span>)}</div>
          </div>
          <div className="chart">
            <Curve rows={rows} budget={budget} max={maxHoles} label={label} color={color} />
          </div>
        </section>

        <aside className="side">
          <section className="panel ratio">
            <span className="label">Holes per tool call</span>
            {ratio !== null ? (
              <>
                <Ticker className="big" value={ratio} format={(v) => `${v.toFixed(1)}×`} ms={1400} />
                <p>
                  more with Muse on the same budget.
                  {fm !== null && fb !== null && ` Muse proved its first hole at call ${fm}, blind BFS at call ${fb}.`}
                  {onlyMuse.length > 0 && ` Only Muse found ${onlyMuse.join(", ")}.`}
                </p>
              </>
            ) : (
              <p>{muse && bfs && !muse.holes ? `Neither mode proved a Class A hole, so there is no ratio to show. Policy vs practice, class B: ${cls("contradictions")}. Ambiguities, class C: ${cls("ambiguities")}.` : muse && bfs ? "Blind BFS found no hole, so there is no ratio to show." : asked && !muse ? "Muse was unavailable, so there is nothing to compare. Check the Meta Model API and run the bench again." : <>This bench has one mode only. Run it with <code translate="no">--modes bfs,muse</code> to compare.</>}</p>
            )}
          </section>
        </aside>
      </div>

      <section className="panel" style={{ overflowX: "auto" }}>
        <table className="btable">
          <caption className="sr-only">Bench results by mode</caption>
          <thead>
            <tr><th>Mode</th><th>Class A holes</th><th>Class B</th><th>Class C</th><th>Tool calls</th><th>Holes per 1,000 calls</th><th>LLM calls</th><th>Tokens</th><th>Wall time</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.mode}>
                <td><b style={{ color: color(r.mode) }}>{label(r.mode)}</b></td>
                <td>{r.holes}</td>
                <td>{r.contradictions ?? "–"}</td>
                <td>{r.ambiguities ?? "–"}</td>
                <td>{int(r.tool_calls)}</td>
                <td>{per1k(r.holes, r.tool_calls).toFixed(2)}</td>
                <td>{int(r.llm_calls)}</td>
                <td>{int(r.tokens)}</td>
                <td>{r.seconds.toFixed(1)} s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

type Row = BenchT["rows"][0];
const W = 720, H = 300, L = 40, B = 28, T = 16, R = 72;

// Cumulative holes proven against tool calls spent, one step line per mode (C5 v1.6 `found`).
// The lines draw in, the found points pop in along them, and a hover guide reads both counts at any budget.
function Curve({ rows, budget, max, label, color }: { rows: Row[]; budget: number; max: number; label: (m: Row["mode"]) => string; color: (m: Row["mode"]) => string }) {
  const svg = useRef<SVGSVGElement>(null), guide = useRef<SVGGElement>(null), tip = useRef<SVGTextElement>(null);
  const dots = useRef<Record<string, SVGCircleElement | null>>({});
  const span = Math.log10(Math.max(budget, 100)) - 1;
  const x = (c: number) => L + ((Math.log10(Math.max(c, 10)) - 1) / span) * (W - L - R);
  const y = (h: number) => H - B - (h / max) * (H - B - T);
  const ticks = [10, 100, 1000, budget].filter((c, i, a) => c <= budget && a.indexOf(c) === i);
  const sorted = (f: { tool_calls: number }[]) => [...f].sort((a, b) => a.tool_calls - b.tool_calls);
  const path = (f: { tool_calls: number }[]) => {
    let d = `M${x(10)},${y(0)}`;
    sorted(f).forEach((p, i) => (d += ` H${x(p.tool_calls)} V${y(i + 1)}`));
    return d + ` H${x(budget)}`;
  };
  const first = (r: Row) => Math.min(...(r.found ?? []).map((f) => f.tool_calls));
  const summary = rows.map((r) => `${label(r.mode)} proves ${r.holes} holes${r.found?.length ? `, the first at call ${first(r)}` : ""}`).join("; ");
  const muse = rows.find((r) => r.mode === "muse" && color(r.mode) === COLOR.muse);

  // Written straight to the SVG through refs: no React render per pointer move.
  const move = (e: PointerEvent<SVGSVGElement>) => {
    const s = svg.current!, m = s.getScreenCTM();
    if (!m) return;
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(m.inverse());
    const gx = Math.min(Math.max(p.x, L), W - R);
    const calls = Math.round(10 ** (1 + ((gx - L) / (W - L - R)) * span));
    const counts = rows.map((r) => [r.mode, (r.found ?? []).filter((f) => f.tool_calls <= calls).length] as const);
    guide.current!.setAttribute("transform", `translate(${gx},0)`);
    guide.current!.style.opacity = "1";
    counts.forEach(([mode, c]) => dots.current[mode]?.setAttribute("cy", String(y(c))));
    const right = gx > W - R - 160;
    tip.current!.textContent = `${int(calls)} calls: ${counts.map(([mode, c]) => `${mode} ${c}`).join(", ")}`;
    tip.current!.setAttribute("text-anchor", right ? "end" : "start");
    tip.current!.setAttribute("x", right ? "-8" : "8");
  };

  return (
    <svg ref={svg} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary} onPointerMove={move} onPointerLeave={() => guide.current && (guide.current.style.opacity = "0")}>
      <defs>
        <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--violet)" stopOpacity=".16" />
          <stop offset="1" stopColor="var(--violet)" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0, Math.round(max / 2), max].map((h) => (
        <g key={h}>
          <line x1={L} x2={W - R} y1={y(h)} y2={y(h)} stroke="var(--line)" strokeDasharray={h ? "3 4" : undefined} />
          <text x={L - 12} y={y(h) + 4} textAnchor="end">{h}</text>
        </g>
      ))}
      {ticks.map((c) => <text key={c} x={x(c)} y={H - 6} textAnchor="middle">{int(c)}</text>)}
      {muse?.found?.length ? <path className="area" d={path(muse.found) + ` V${y(0)} Z`} fill="url(#area)" /> : null}
      {rows.map((r, i) => (
        <g key={r.mode}>
          <path className="draw" pathLength={1} d={path(r.found ?? [])} fill="none" stroke={color(r.mode)} strokeWidth={r.mode === "muse" ? 2.5 : 1.75} strokeLinejoin="round" />
          {sorted(r.found ?? []).map((p, i) => (
            <circle key={i} className="dot" cx={x(p.tool_calls)} cy={y(i + 1)} r={r.mode === "muse" ? 3 : 2.5} fill={color(r.mode)}
              style={{ animationDelay: `${0.3 + ((x(p.tool_calls) - L) / (W - L - R)) * 1.6}s` }} />
          ))}
          <text x={x(budget) + 12} y={y(r.found?.length ?? 0) + (i && (rows[0].found?.length ?? 0) === (r.found?.length ?? 0) ? -10 : 4)} style={{ fill: color(r.mode), fontWeight: 700 }}>{r.found?.length ?? 0} {r.mode}</text>
        </g>
      ))}
      <g ref={guide} className="guide" aria-hidden="true">
        <line y1={T} y2={H - B} stroke="var(--muted)" strokeDasharray="2 3" />
        {rows.map((r) => <circle key={r.mode} ref={(el) => void (dots.current[r.mode] = el)} r="5" fill="var(--surface)" stroke={color(r.mode)} strokeWidth="2" />)}
        <text ref={tip} y={T + 4} x="8" />
      </g>
    </svg>
  );
}
