import type { ReactNode } from "react";
import { ArrowRight, Check, FileSearch, ShieldCheck } from "lucide-react";
import { api, useGet, type Domain, type Hole, type Load, type Ratified, type Report } from "../api";
import { Crumbs, Failure, Loading, Muse, holeHref, humanize, int, quote, usd, when } from "../ui";

const CLASS_C_NOTE = "Cancel and rebook inside a permitted cancel ground is the method the policy allows. Listed for review, not counted.";

export function ReportView({ domain, report }: { domain: Domain; report: Load<Report> }) {
  const ratified = useGet<Ratified>(api.ratified(domain));
  const fixed = new Set(ratified.data?.amendments.map((a) => a.hole_key));
  const goals = new Map(ratified.data?.ruleset.forbidden_goals.map((g) => [g.id, g]));

  if (report.loading) return <Page domain={domain}><Loading what={`the latest ${domain} report`} /></Page>;
  if (report.error?.status === 404)
    return (
      <Page domain={domain}>
        <h1 className="title">No {domain} report yet</h1>
        <section className="panel empty-state">
          <span className="shield"><FileSearch size={30} aria-hidden="true" /></span>
          <h2 className="h2">Run an audit to see which chains of allowed calls break the {domain} policy</h2>
          <a className="btn primary" href="#/">Run an audit</a>
        </section>
      </Page>
    );
  if (!report.data) return <Page domain={domain}><Failure error={report.error!} onRetry={report.reload} /></Page>;

  const { run, holes, ambiguities, stats } = report.data;
  const byGoal = new Map<string, Hole[]>();
  for (const h of holes) byGoal.set(h.goal, [...(byGoal.get(h.goal) ?? []), h]);
  const paid = holes.reduce((a, h) => a + h.money_delta, 0);

  return (
    <Page domain={domain}>
      <div className="head">
        <div>
          <h1 className="title">
            {holes.length ? <><span className="r">{holes.length} proven {holes.length === 1 ? "hole" : "holes"}</span> in the {domain} policy</> : <>No proven holes in the {domain} policy</>}
          </h1>
          <p className="lede">
            {holes.length
              ? "Every hole below is a chain of tool calls the policy allows, one by one, that ends in an outcome the policy forbids. Each was replayed five times on a fresh database."
              : "A hole is a chain of tool calls the policy allows, one by one, that ends in an outcome the policy forbids. This run proved none."}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {run.mode === "muse" ? (
            <>
              <Muse>Rules compiled by Muse Spark</Muse>
              <Muse>Chains proposed by Muse Spark</Muse>
            </>
          ) : (
            <span className="tag">Offline run · hand RuleSet, blind BFS</span>
          )}
          {holes.some((h) => h.amendment) && <Muse>Amendments drafted by Muse Spark</Muse>}
        </div>
      </div>

      <div className="summary">
        <div>
          <span className="label">Run</span>
          <span className="mono" style={{ fontSize: 13 }}>{when(run.started)}{run.commit && ` · ${run.commit.slice(0, 7)}`}</span>
          <span className="s">mode {run.mode}{run.model && ` · model ${run.model}`} · {int(stats.tokens)} tokens</span>
        </div>
        <div><span className="label">Class A holes</span><span className={`v ${holes.length ? "r" : ""}`}>{holes.length}</span><span className="s">{byGoal.size} forbidden {byGoal.size === 1 ? "goal" : "goals"} reached</span></div>
        <div><span className="label">Net paid out</span><span className="v">{usd(paid)}</span><span className="s">refunds minus charges, all holes</span></div>
        <div><span className="label">Search</span><span className="v num">{int(stats.tool_calls)}</span><span className="s">tool calls of {int(run.budget)} · {Math.round(stats.seconds)} s</span></div>
      </div>

      {[...byGoal].map(([gid, list]) => {
        const g = goals.get(gid);
        const name = g ? humanize(g.name).name : humanize(list[0].title).name;
        return (
          <section key={gid} className="goal-group" aria-labelledby={`g-${gid}`}>
            <div className="hcard goal-card">
              <div className="top">
                <span className="id">{gid} · class A · {list.length} {list.length === 1 ? "booking" : "bookings"}</span>
                <i className="hole-mark" aria-hidden="true" />
              </div>
              <h2 id={`g-${gid}`} className="h3">{name}</h2>
              {g && <p className="quote">{quote(g.policy_ref)}</p>}
            </div>
            <ul className="instances">
              {list.map((h) => (
                <li key={h.key}>
                  <a href={holeHref(domain, h.key)}>
                    <span className="mono k">{h.id}</span>
                    <span className="mono t" translate="no">{humanize(h.title, h.key).target}</span>
                    <span className="mono c">{h.chain.map((s) => s.tool).join(" → ")}</span>
                    <span className={`m ${h.money_delta > 0 ? "out" : ""}`}>{usd(h.money_delta)}</span>
                    <span className="rep">{h.replays}</span>
                    {fixed.has(h.key) ? <span className="tag green"><Check size={13} aria-hidden="true" />Fixed</span> : h.amendment ? <span className="tag muse">Amendment ready</span> : <span />}
                    <ArrowRight size={15} aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      {!holes.length && (
        <section className="panel empty-state">
          <span className="shield"><ShieldCheck size={32} aria-hidden="true" /></span>
          <h2 className="h2">The search spent its budget without reaching a forbidden outcome</h2>
          <p>{int(stats.chains_tried)} chains over every write tool. This is not a proof that no hole exists. Raise the budget or add forbidden goals, then run the audit again.</p>
          <a className="btn" href="#/">Run another audit</a>
        </section>
      )}

      {ambiguities.length > 0 && (
        <section className="panel" aria-labelledby="amb-h">
          <div className="panel-h">
            <h2 id="amb-h">Ambiguities · class C, not counted</h2>
            <span className="label">{ambiguities.length} listed for review</span>
          </div>
          <p style={{ padding: "12px 18px 4px", color: "var(--muted)", fontSize: 14 }}>{CLASS_C_NOTE}</p>
          <ul className="amb">
            {ambiguities.map((a) => {
              const t = humanize(a.title, a.key);
              return (
                <li key={a.key}>
                  <span className="id">{a.id}</span>
                  <span>
                    <span className="t">{t.name} <span className="mono" style={{ color: "var(--muted)" }}>{t.target}</span></span>
                    <br />
                    <span className="c">{a.chain.map((s) => s.tool).join(" → ")}</span>
                  </span>
                  <span className="tag">{a.goal} · {a.replays}</span>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </Page>
  );
}

function Page({ domain, children }: { domain: Domain; children: ReactNode }) {
  return (
    <div className="page">
      <Crumbs items={[["Audit", "#/"], [`${domain} report`]]} />
      {children}
    </div>
  );
}
