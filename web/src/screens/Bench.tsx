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
  const maxRate = Math.max(0.001, ...rows.map((r) => per1k(r.holes, r.tool_calls)));
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
            <h2>Holes proven</h2>
            <div className="legend">{rows.map((r) => <span key={r.mode}><i style={{ background: COLOR[r.mode] }} />{LABEL[r.mode]}</span>)}</div>
          </div>
          <div className="bars">
            {[
              { name: "Holes found", v: (r: (typeof rows)[0]) => r.holes, max: maxHoles, fmt: (x: number) => int(x) },
              { name: "Holes per 1,000 tool calls", v: (r: (typeof rows)[0]) => per1k(r.holes, r.tool_calls), max: maxRate, fmt: (x: number) => x.toFixed(2) },
            ].map((m) => (
              <div key={m.name} className="bar-group">
                <span className="label">{m.name}</span>
                {rows.map((r) => (
                  <div key={r.mode} className="bar-row">
                    <span className="mono">{LABEL[r.mode]}</span>
                    <span className="track"><i style={{ width: `${(m.v(r) / m.max) * 100}%`, background: COLOR[r.mode] }} /></span>
                    <b className="num">{m.fmt(m.v(r))}</b>
                  </div>
                ))}
              </div>
            ))}
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
