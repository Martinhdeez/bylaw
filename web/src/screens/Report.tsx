import type { CSSProperties, ReactNode } from "react";
import { AlertTriangle, ArrowRight, ChevronRight, FileSearch, ShieldCheck } from "lucide-react";
import { api, useGet, type Domain, type ForbiddenGoal, type Hole, type Load, type Ratified, type Report } from "../api";
import { Crumbs, Failure, Loading, Muse, Ticker, chainText, classCWhy, goldLine, holeHref, humanize, int, quote, usd, when } from "../ui";

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
          <span className="shield"><FileSearch aria-hidden="true" /></span>
          <h2 className="h2">Run an audit to see which chains of allowed calls break the {domain} policy</h2>
          <p>An audit compiles the policy, searches up to the budget and proves every hit five times.</p>
          <a className="btn primary" href="#/">Run an audit<span className="ic"><ArrowRight aria-hidden="true" /></span></a>
        </section>
      </Page>
    );
  if (!report.data) return <Page domain={domain}><Failure error={report.error!} onRetry={report.reload} /></Page>;

  const { run, holes, ambiguities, stats } = report.data;
  const contradictions = report.data.contradictions ?? [];
  const paid = holes.reduce((a, h) => a + h.money_delta, 0);
  const all = [...holes, ...contradictions];
  const goalCount = new Set(holes.map((h) => h.goal)).size;

  return (
    <Page domain={domain}>
      <div className="head">
        <div>
          <h1 className="title">
            {holes.length ? <><span className="r">{holes.length} proven {holes.length === 1 ? "hole" : "holes"}</span> in the {domain} policy</> : <>No proven holes in the {domain} policy</>}
          </h1>
          <p className="lede">
            {holes.length
              ? "Every hole below is a chain of tool calls the policy allows, one by one, that ends in an outcome the policy forbids, and that no gold task of the benchmark takes. Each was replayed five times on a fresh database."
              : "A hole is a chain of tool calls the policy allows, one by one, that ends in an outcome the policy forbids, and that no gold task of the benchmark takes. This run proved none."}
            {contradictions.length > 0 && ` ${contradictions.length} ${contradictions.length === 1 ? "finding is" : "findings are"} policy vs practice instead: a gold task of the benchmark reaches the same outcome, so the policy and the benchmark's practice disagree.`}
          </p>
        </div>
        <div className="tags">
          {run.mode === "muse" ? (
            <>
              <Muse>Rules compiled by Muse Spark</Muse>
              <Muse>Chains proposed by Muse Spark</Muse>
            </>
          ) : (
            <span className="tag">Offline run: hand RuleSet, blind BFS</span>
          )}
          {all.some((h) => h.amendment) && <Muse>Amendments drafted by Muse Spark</Muse>}
        </div>
      </div>

      {run.mode === "bfs-fallback" && (
        <div className="notice warn" role="note" data-testid="muse-unavailable">
          <AlertTriangle aria-hidden="true" />
          <div>
            <b>Muse unavailable.</b>
            <p>This audit asked for Muse Spark, but {stats.llm_calls === 1 ? "its one call" : `all ${int(stats.llm_calls)} calls`} failed{stats.llm_errors ? ` (${int(stats.llm_errors)} errors)` : ""}, so it ran offline: the hand RuleSet and blind BFS. Check the Meta Model API and run the audit again for Muse-guided results.</p>
          </div>
        </div>
      )}

      <div className="summary">
        <div className="panel stat">
          <span className="label">Run</span>
          <span className="mono" style={{ fontSize: 13 }}>{when(run.started)}{run.commit && `, ${run.commit.slice(0, 7)}`}</span>
          <span className="s" data-testid="run-meta">
            mode {run.mode}{run.model ? `, model ${run.model}` : ""}{run.effort ? `, effort ${run.effort}` : ""}, {int(stats.tokens)} tokens
            {run.mode === "muse" && `, peak context ${run.context_tokens == null ? "unknown" : `${int(run.context_tokens)} tokens`}`}
          </span>
        </div>
        <div className="panel stat"><span className="label">Class A holes</span><Ticker className={`v ${holes.length ? "r" : ""}`} value={holes.length} /><span className="s">{goalCount} forbidden {goalCount === 1 ? "goal" : "goals"} reached</span></div>
        <div className="panel stat"><span className="label">Policy vs practice</span><Ticker className={`v ${contradictions.length ? "b" : ""}`} value={contradictions.length} /><span className="s">class B, gold tasks do it too</span></div>
        <div className="panel stat"><span className="label">Search</span><Ticker className="v" value={stats.tool_calls} /><span className="s">tool calls of {int(run.budget)} in {Math.round(stats.seconds)} s</span></div>
      </div>

      {holes.length > 0 && (
        <>
          <p className="section-note"><b>Holes.</b> Net paid out across all of them: {usd(paid)} (refunds minus charges, from the replayed database).</p>
          <Groups domain={domain} entries={holes} goals={goals} fixed={fixed} />
        </>
      )}

      {!holes.length && !contradictions.length && (
        <section className="panel empty-state">
          <span className="shield"><ShieldCheck aria-hidden="true" /></span>
          <h2 className="h2">The search spent its budget without reaching a forbidden outcome</h2>
          <p>{int(stats.chains_tried)} chains over every write tool. This is not a proof that no hole exists. Raise the budget or add forbidden goals, then run the audit again.</p>
          <a className="btn" href="#/">Run another audit</a>
        </section>
      )}

      {contradictions.length > 0 && (
        <section className="practice" aria-labelledby="pvp-h">
          <div>
            <h2 id="pvp-h" className="title sm">Policy vs <span className="b">practice</span></h2>
            <p className="lede">The benchmark's gold tasks reach these outcomes and τ² grades them as correct: where the policy is silent or ambiguous, its practice reads it permissively. They are not counted as holes. Each needs a decision: amend the text to match practice, or ratify the rule and accept the gold tasks it blocks.</p>
          </div>
          <Groups domain={domain} entries={contradictions} goals={goals} fixed={fixed} />
        </section>
      )}

      {ambiguities.length > 0 && (
        <section className="panel amb-panel" aria-labelledby="amb-h">
          <div className="panel-h">
            <h2 id="amb-h">Ambiguities, class C, not counted</h2>
            <span className="label">{ambiguities.length} listed for review</span>
          </div>
          {[...byGoal(ambiguities)].map(([gid, list]) => (
            <details key={gid} className="amb-goal" data-testid="amb-goal">
              <summary>
                <span className="id">{gid}</span>
                <span>
                  <span className="t">{humanize(goals.get(gid)?.name ?? list[0].title).name}</span>
                  <span className="n" data-testid="amb-note">{new Set(list.map(classCWhy)).size === 1 ? `${capital(classCWhy(list[0]))}.` : "The reason differs by entry, see each one."}</span>
                </span>
                <span className="tag">{list.length} {list.length === 1 ? "entry" : "entries"}</span>
                <ChevronRight aria-hidden="true" />
              </summary>
              <ul className="amb">
                {list.map((a) => {
                  const t = humanize(a.title, a.key);
                  return (
                    <li key={a.key}>
                      <a href={holeHref(domain, a.key)}>
                        <span className="id">{a.id}</span>
                        <span>
                          <span className="t">{t.name} <span className="mono" style={{ color: "var(--muted)" }}>{t.target}</span></span>
                          <br />
                          <span className="c">{chainText(a.chain)}</span>
                          <br />
                          <span className="n" data-testid="amb-entry-note">{capital(classCWhy(a))}.</span>
                        </span>
                        <span className="tag">{a.replays}</span>
                      </a>
                    </li>
                  );
                })}
              </ul>
            </details>
          ))}
        </section>
      )}
    </Page>
  );
}

const capital = (t: string) => t[0].toUpperCase() + t.slice(1);

// One card per forbidden goal, with the bookings it was proven on.
const byGoal = (entries: Hole[]) => {
  const m = new Map<string, Hole[]>();
  for (const h of entries) m.set(h.goal, [...(m.get(h.goal) ?? []), h]);
  return m;
};

function Groups({ domain, entries, goals, fixed }: { domain: Domain; entries: Hole[]; goals: Map<string, ForbiddenGoal>; fixed: Set<string> }) {
  return (
    <>
      {[...byGoal(entries)].map(([gid, list]) => {
        const g = goals.get(gid);
        const b = list[0].class === "B";
        const tasks = [...new Set(list.flatMap((h) => h.gold?.tasks ?? []))];
        return (
          <section key={gid} className={`goal-group ${b ? "cls-b" : ""}`} aria-labelledby={`g-${gid}-${list[0].class}`}>
            <div className="panel gcard">
              <div className="top">
                <span className="id">{gid} · class {list[0].class} · {list.length} {list.length === 1 ? "booking" : "bookings"}</span>
                <i className={b ? "b-mark" : "hole-mark"} aria-hidden="true" />
              </div>
              <h3 id={`g-${gid}-${list[0].class}`}>{g ? humanize(g.name).name : humanize(list[0].title).name}</h3>
              {g && <p className="quote">{quote(g.policy_ref)}</p>}
              {b && tasks.length > 0 && <p className="gold">{goldLine(tasks)}</p>}
            </div>
            <ul className="panel instances">
              {list.map((h, i) => {
                const chain = chainText(h.chain);
                return (
                  <li key={h.key} style={{ "--i": i } as CSSProperties}>
                    <a href={holeHref(domain, h.key)}>
                      <span className="mono k">{h.id}</span>
                      <span className="mono t" translate="no">{humanize(h.title, h.key).target}</span>
                      <span className="c" title={chain}>{chain}</span>
                      <span className={`m ${!b && h.money_delta > 0 ? "out" : ""}`}>{usd(h.money_delta)}</span>
                      <span className="rep">{h.replays}</span>
                      {fixed.has(h.key) ? <span className="tag stamped">{b ? "Ratified" : "Fixed"}</span> : h.amendment ? <span className="tag muse">Amendment ready</span> : <span />}
                      <ArrowRight aria-hidden="true" />
                    </a>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </>
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
