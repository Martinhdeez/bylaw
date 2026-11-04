import { useEffect, useRef, useState } from "react";
import { ExternalLink, Receipt } from "lucide-react";
import { api, useGet, type Usage as UsageT, type UsageEntry } from "../api";
import { Crumbs, Failure, Loading, Muse, Ticker, int } from "../ui";

const EVERY = 5000;
const usd = (n: number) => `$${n.toFixed(4)}`;
const cost = (c: { low: number; high: number }) => (c.low === c.high ? usd(c.low) : `${usd(c.low)}–${usd(c.high)}`);
const day = (iso: string) => new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" }).format(new Date(iso));
const pct = (a: number, b: number) => (b ? Math.min(100, (a / b) * 100) : 0);

// GET /api/usage, again every 5 s while the tab is visible; a failed refresh keeps the last answer on screen.
function usePolled() {
  const u = useGet<UsageT>(api.usage());
  const last = useRef<UsageT>();
  const [at, setAt] = useState<Date>();
  if (u.data && u.data !== last.current) last.current = u.data;
  useEffect(() => void (u.data && setAt(new Date())), [u.data]);
  useEffect(() => {
    const id = setInterval(() => document.visibilityState === "visible" && u.reload(), EVERY);
    const back = () => document.visibilityState === "visible" && u.reload();
    addEventListener("visibilitychange", back);
    return () => { clearInterval(id); removeEventListener("visibilitychange", back); };
  }, []);
  return { ...u, data: last.current, stale: !!(last.current && u.error), at };
}

export function Usage() {
  const u = usePolled();
  const crumbs = <Crumbs items={[["Usage"]]} />;
  if (!u.data && u.loading) return <div className="page">{crumbs}<Loading what="usage" shape="bench" /></div>;
  if (!u.data) return <div className="page">{crumbs}<Failure error={u.error!} onRetry={u.reload} /></div>;

  const { price, recorded, live } = u.data;
  const ranged = recorded.entries.some((e) => e.cost_usd.low !== e.cost_usd.high);

  return (
    <div className="page usage">
      {crumbs}
      <div className="head">
        <div>
          <h1 className="title">Muse Spark usage and cost</h1>
          <p className="lede">Every Muse Spark token bylaw spends: the public deploy since its API started, and the recorded runs behind the committed reports. Costs are estimates from the published price, not an invoice.</p>
        </div>
        <Muse>{price.model}</Muse>
      </div>

      <section className="panel price" aria-label="Muse Spark price">
        <div><span className="label">Input</span><b>${price.input_per_1m.toFixed(2)}</b><span className="s">per 1M tokens</span></div>
        <div><span className="label">Output</span><b>${price.output_per_1m.toFixed(2)}</b><span className="s">per 1M tokens</span></div>
        <p>
          Meta Model API price for {price.model}, read on {day(price.read)}.{" "}
          <a href={price.source} target="_blank" rel="noreferrer">Pricing page<ExternalLink aria-hidden="true" /><span className="sr-only"> (opens in a new tab)</span></a>
        </p>
      </section>

      <section className="panel">
        <div className="panel-h">
          <h2>Public deploy</h2>
          {!live.enabled ? (
            <span className="status">Live runs off</span>
          ) : u.stale ? (
            <span className="status error"><i />Refresh failed, showing {u.at ? u.at.toLocaleTimeString("en-GB") : "the last answer"}</span>
          ) : (
            <span className="status running"><i />Refreshing every 5 s</span>
          )}
        </div>
        {live.enabled ? <Live l={live} /> : (
          <p className="panel-b muted">This deploy runs with live sessions turned off, so it spends no Muse Spark tokens. The recorded runs below still apply.</p>
        )}
      </section>

      <section className="panel">
        <div className="panel-h">
          <h2>Recorded runs</h2>
          <span className="label">{recorded.entries.length} {recorded.entries.length === 1 ? "entry" : "entries"}, from reports/usage.json</span>
        </div>
        {recorded.entries.length ? (
          <>
            <table className="btable ledger">
              <caption className="sr-only">Muse Spark usage by recorded run, with totals</caption>
              <thead>
                <tr><th>Run</th><th>Calls</th><th>Input</th><th>Output</th><th>Tokens</th><th>Time</th><th>Estimated cost</th></tr>
              </thead>
              <tbody>{recorded.entries.map((e) => <Row key={e.id} e={e} />)}</tbody>
              <tfoot>
                <tr>
                  <th scope="row">Total</th>
                  <td data-l="Calls">{int(recorded.total.calls)}</td>
                  <td className="na" /><td className="na" />
                  <td data-l="Tokens">{int(recorded.total.tokens)}</td>
                  <td className="na" />
                  <td data-l="Estimated cost"><span>{cost(recorded.total.cost_usd)}{recorded.total.cost_usd.low !== recorded.total.cost_usd.high && <sup>*</sup>}</span></td>
                </tr>
              </tfoot>
            </table>
            {ranged && (
              <p className="foot-note"><sup>*</sup> These sources record only the total tokens, not the input/output split, so the cost is a range: all of it billed as input (${price.input_per_1m.toFixed(2)} per 1M) up to all of it billed as output (${price.output_per_1m.toFixed(2)} per 1M).</p>
            )}
          </>
        ) : (
          <div className="empty-state">
            <span className="shield"><Receipt aria-hidden="true" /></span>
            <p>No recorded runs. This deploy has no <code translate="no">reports/usage.json</code>, so only the live counters above count.</p>
          </div>
        )}
      </section>
    </div>
  );
}

function Live({ l }: { l: UsageT["live"] }) {
  const used = pct(l.tokens_used, l.token_cap);
  const tone = used >= 100 ? "r" : used >= 80 ? "b" : "";
  return (
    <div className="panel-b live-use">
      <div className="cap">
        <div className="cap-h">
          <span className="label">Tokens used of the cap</span>
          <span className={"cap-v " + tone}><Ticker value={l.tokens_used} testId="usage-tokens" /> <span>of {int(l.token_cap)}</span></span>
        </div>
        <div className={"cap-bar " + tone} role="meter" aria-label="Tokens used of the cap" aria-valuemin={0} aria-valuemax={l.token_cap} aria-valuenow={l.tokens_used}
          aria-valuetext={`${int(l.tokens_used)} of ${int(l.token_cap)} tokens, ${used.toFixed(1)}%`}>
          <i className="in" style={{ width: `${pct(l.input_tokens, l.token_cap)}%` }} />
          <i className="out" style={{ width: `${pct(l.output_tokens, l.token_cap)}%` }} />
        </div>
        <div className="cap-f">
          <span><i className="in" />Input {int(l.input_tokens)}</span>
          <span><i className="out" />Output {int(l.output_tokens)}</span>
          <span className="pct">{used >= 100 ? "Cap reached" : `${used.toFixed(1)}% used`}</span>
        </div>
      </div>
      <div className="figs">
        <div><span className="label">Sessions</span><Ticker className="v" value={l.sessions} /></div>
        <div><span className="label">Estimated cost</span><Ticker className="v" value={l.cost_usd} format={usd} testId="usage-cost" /></div>
      </div>
    </div>
  );
}

const sec = (s: number) => (s >= 60 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${s.toFixed(1)} s`);
const opt = (n: number | null, f: (n: number) => string = int) => (n === null ? <span className="na" title="not recorded">–</span> : f(n));

function Row({ e }: { e: UsageEntry }) {
  const split = e.input_tokens !== null && e.output_tokens !== null;
  return (
    <tr>
      <th scope="row">
        <div className="run">
          <span className={"stage s-" + e.stage}>{e.stage}</span>
          <b>{e.label}</b>
          <code translate="no">{e.source}</code>
        </div>
      </th>
      <td data-l="Calls">{opt(e.calls)}</td>
      <td data-l="Input">{opt(e.input_tokens)}</td>
      <td data-l="Output">{opt(e.output_tokens)}</td>
      <td data-l="Tokens">{int(e.tokens)}</td>
      <td data-l="Time">{opt(e.seconds, sec)}</td>
      <td data-l="Estimated cost"><span>{cost(e.cost_usd)}{!split && e.cost_usd.low !== e.cost_usd.high && <sup>*</sup>}</span></td>
    </tr>
  );
}
