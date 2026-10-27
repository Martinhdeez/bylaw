import { Gauge } from "lucide-react";
import { api, useGet, type Bench as BenchT, type Domain } from "../api";
import { Crumbs, Failure, Loading, Muse, int } from "../ui";

const LABEL = { muse: "Muse-guided", bfs: "Blind BFS" } as const;
const COLOR = { muse: "var(--blue)", bfs: "var(--muted)" } as const;
const per1k = (holes: number, calls: number) => (calls ? (holes / calls) * 1000 : 0);

export function Bench({ domain }: { domain: Domain }) {
  const bench = useGet<BenchT>(api.bench(domain));
  const crumbs = <Crumbs items={[[`${domain} bench`]]} />;

  if (bench.loading) return <div className="page">{crumbs}<Loading what="the bench" /></div>;
  if (bench.error?.status === 404)
    return (
      <div className="page">
        {crumbs}
        <h1 className="title">No {domain} bench yet</h1>
        <section className="panel empty-state">
          <span className="shield"><Gauge size={30} aria-hidden="true" /></span>
          <p>The bench compares Muse-guided search with blind BFS on the same budget. Produce it with <code translate="no">uv run python -m bylaw bench --domain {domain} --budget 2000</code>.</p>
        </section>
      </div>
    );
  if (!bench.data) return <div className="page">{crumbs}<Failure error={bench.error!} onRetry={bench.reload} /></div>;

  const { rows, budget } = bench.data;
  const muse = rows.find((r) => r.mode === "muse");
  const bfs = rows.find((r) => r.mode === "bfs");
  const maxHoles = Math.max(1, ...rows.map((r) => r.holes));
  const ratio = muse && bfs && per1k(bfs.holes, bfs.tool_calls) > 0 ? per1k(muse.holes, muse.tool_calls) / per1k(bfs.holes, bfs.tool_calls) : null;
  const onlyMuse = muse && bfs ? muse.hole_keys.filter((k) => !bfs.hole_keys.includes(k)) : [];

  return (
    <div className="page">
      {crumbs}
      <div className="head">
        <div>
          <h1 className="title">Muse-guided search against blind BFS</h1>
          <p className="lede">Same {domain} policy, same budget of {int(budget)} tool calls, same depth limit. Muse Spark proposes chains per forbidden goal before BFS fills the rest of the budget.</p>
        </div>
        {muse && <Muse>Chains proposed by Muse Spark · high reasoning</Muse>}
      </div>

      <div className="bench">
        <section className="panel">
          <div className="panel-h">
            <h2>Holes proven by tool calls spent <span className="label">(log scale)</span></h2>
            <div className="legend">{rows.map((r) => <span key={r.mode}><i style={{ background: COLOR[r.mode] }} />{LABEL[r.mode]}</span>)}</div>
          </div>
          <div className="chart">
            <Curve rows={rows} budget={budget} max={maxHoles} />
          </div>
        </section>

        <aside className="side">
          <section className="panel ratio">
            <span className="label">Holes per tool call</span>
            {ratio !== null ? (
              <>
                <span className="big">{ratio.toFixed(1)}×</span>
                <span style={{ color: "var(--muted)", fontSize: 14 }}>
                  more with Muse on the same budget.{onlyMuse.length > 0 && ` Only Muse found ${onlyMuse.join(", ")}.`}
                </span>
              </>
            ) : (
              <span style={{ color: "var(--muted)", fontSize: 14 }}>{muse && bfs ? "Blind BFS found no hole, so there is no ratio to show." : "This bench has one mode only; run it with --modes bfs,muse to compare."}</span>
            )}
          </section>
        </aside>
      </div>

      <section className="panel" style={{ overflowX: "auto" }}>
        <table className="btable">
          <caption className="sr-only">Bench results by mode</caption>
          <thead>
            <tr><th>Mode</th><th>Holes found</th><th>Tool calls</th><th>Holes per 1,000 calls</th><th>LLM calls</th><th>Tokens</th><th>Wall time</th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.mode}>
                <td><b style={{ color: COLOR[r.mode] }}>{LABEL[r.mode]}</b></td>
                <td>{r.holes}</td>
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
const W = 720, H = 300, L = 40, B = 28, T = 14, R = 70;

// Cumulative holes proven against write steps spent, one step line per mode (C5 v1.6 `found`).
function Curve({ rows, budget, max }: { rows: Row[]; budget: number; max: number }) {
  const x = (c: number) => L + ((Math.log10(Math.max(c, 10)) - 1) / (Math.log10(Math.max(budget, 100)) - 1)) * (W - L - R);
  const y = (h: number) => H - B - (h / max) * (H - B - T);
  const ticks = [10, 100, 1000, budget].filter((c, i, a) => c <= budget && a.indexOf(c) === i);
  const path = (f: { tool_calls: number }[]) => {
    let d = `M${x(10)},${y(0)}`;
    [...f].sort((a, b) => a.tool_calls - b.tool_calls).forEach((p, i) => (d += ` H${x(p.tool_calls)} V${y(i + 1)}`));
    return d + ` H${x(budget)}`;
  };
  const first = (r: Row) => Math.min(...(r.found ?? []).map((f) => f.tool_calls));
  const summary = rows.map((r) => `${LABEL[r.mode]} proves ${r.holes} holes${r.found?.length ? `, the first at call ${first(r)}` : ""}`).join("; ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={summary}>
      {[0, Math.round(max / 2), max].map((h) => (
        <g key={h}>
          <line x1={L} x2={W - R} y1={y(h)} y2={y(h)} stroke="var(--line)" strokeDasharray={h ? "3 4" : undefined} />
          <text x={L - 10} y={y(h) + 4} textAnchor="end">{h}</text>
        </g>
      ))}
      {ticks.map((c) => <text key={c} x={x(c)} y={H - 6} textAnchor="middle">{int(c)}</text>)}
      {rows.map((r) => (
        <g key={r.mode}>
          <path d={path(r.found ?? [])} fill="none" stroke={COLOR[r.mode]} strokeWidth={r.mode === "muse" ? 3 : 2} />
          <text x={x(budget) + 8} y={y(r.found?.length ?? 0) + 4} style={{ fill: COLOR[r.mode], fontWeight: 700 }}>{r.found?.length ?? 0} {r.mode}</text>
        </g>
      ))}
    </svg>
  );
}
