import { BENCH } from "../fixtures";
import { Crumbs, Muse, int } from "../ui";

const W = 720, H = 300, L = 36, B = 28, T = 12, R = 16;
// Log scale: the interesting part is the first few hundred calls.
const x = (c: number) => L + ((Math.log10(Math.max(c, 10)) - 1) / (Math.log10(BENCH.budget) - 1)) * (W - L - R);
const y = (h: number) => H - B - (h / 3) * (H - B - T);

function steps(found: { call: number }[]) {
  let d = `M${x(10)},${y(0)}`;
  found.forEach((f, i) => (d += ` H${x(f.call)} V${y(i + 1)}`));
  return d + ` H${x(BENCH.budget)}`;
}

export function Bench() {
  const [muse, bfs] = BENCH.rows;
  const color = { muse: "var(--blue)", bfs: "var(--muted)" };
  const speedup = (bfs.found_at[0].call / muse.found_at[0].call).toFixed(1);

  return (
    <div className="page">
      <Crumbs items={[["Bench"]]} />
      <div className="head">
        <div>
          <h1 className="title">Muse-guided search against blind BFS</h1>
          <p className="lede">Same airline policy, same budget of {int(BENCH.budget)} tool calls, same depth limit. Muse Spark proposes chains per forbidden goal before BFS fills the rest of the budget.</p>
        </div>
        <Muse>Chains proposed by Muse Spark · high reasoning</Muse>
      </div>

      <div className="bench">
        <section className="panel">
          <div className="panel-h">
            <h2>Holes proven by tool calls spent <span className="label">(log scale)</span></h2>
            <div className="legend">
              <span><i style={{ background: color.muse }} />Muse-guided</span>
              <span><i style={{ background: color.bfs }} />Blind BFS</span>
            </div>
          </div>
          <div className="chart">
            <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Muse-guided finds 3 holes by call ${muse.found_at[2].call}; blind BFS finds 2 holes by call ${bfs.found_at[1].call}.`}>
              {[0, 1, 2, 3].map((h) => (
                <g key={h}>
                  <line x1={L} x2={W - R} y1={y(h)} y2={y(h)} stroke="var(--line)" strokeDasharray={h ? "3 4" : undefined} />
                  <text x={L - 10} y={y(h) + 4} textAnchor="end">{h}</text>
                </g>
              ))}
              {[10, 100, 1000, 2000].map((c) => (
                <text key={c} x={x(c)} y={H - 6} textAnchor="middle">{int(c)}</text>
              ))}
              {BENCH.rows.map((r) => (
                <g key={r.mode}>
                  <path d={steps(r.found_at)} fill="none" stroke={color[r.mode]} strokeWidth={r.mode === "muse" ? 3 : 2} />
                  {r.found_at.map((f, i) => (
                    <g key={f.hole}>
                      <circle cx={x(f.call)} cy={y(i + 1)} r="5" fill="var(--ground)" stroke={color[r.mode]} strokeWidth="2.5" />
                      <text x={x(f.call) + 8} y={y(i + 1) - 8} style={{ fill: color[r.mode] }}>{f.hole} @{f.call}</text>
                    </g>
                  ))}
                </g>
              ))}
            </svg>
          </div>
        </section>

        <aside className="side">
          <section className="panel ratio">
            <span className="label">Tool calls to the first hole</span>
            <span className="big">{speedup}×</span>
            <span style={{ color: "var(--muted)", fontSize: 14 }}>fewer with Muse: call {muse.found_at[0].call} against call {bfs.found_at[0].call}. Blind BFS never reaches H1 within the budget.</span>
          </section>
        </aside>
      </div>

      <section className="panel" style={{ overflowX: "auto" }}>
        <table className="btable">
          <caption className="sr-only">Bench results by mode</caption>
          <thead>
            <tr><th>Mode</th><th>Holes found</th><th>Tool calls</th><th>Holes per 1,000 calls</th><th>LLM calls</th><th>Wall time</th></tr>
          </thead>
          <tbody>
            {BENCH.rows.map((r) => (
              <tr key={r.mode}>
                <td><b style={{ color: color[r.mode] }}>{r.mode === "muse" ? "Muse-guided" : "Blind BFS"}</b></td>
                <td>{r.holes}</td>
                <td>{int(r.tool_calls)}</td>
                <td>{((r.holes / r.tool_calls) * 1000).toFixed(2)}</td>
                <td>{r.llm_calls}</td>
                <td>{r.seconds.toFixed(1)} s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
