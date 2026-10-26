import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { FileWarning, FlaskConical, Gauge, PlayCircle, Sparkles } from "lucide-react";
import { AIRLINE, type Report } from "./fixtures";
import { Logo, int } from "./ui";
import { Audit } from "./screens/Audit";
import { ReportView } from "./screens/Report";
import { HoleView } from "./screens/Hole";
import { AmendmentView } from "./screens/Amendment";
import { Bench } from "./screens/Bench";
import "./styles.css";

const useHash = () => {
  const [h, set] = useState(location.hash.slice(1) || "/");
  useEffect(() => {
    const on = () => {
      set(location.hash.slice(1) || "/");
      window.scrollTo(0, 0);
    };
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  return h;
};

function App() {
  const path = useHash();
  const [report, setReport] = useState<Report>(AIRLINE);
  const [ratified, setRatified] = useState<string[]>([]);
  const [, section, id, sub] = path.split("/");

  const hole = report.holes.find((h) => h.id === id);
  let page;
  if (section === "report") page = <ReportView report={report} ratified={ratified} />;
  else if (section === "holes" && hole && sub === "amendment")
    page = <AmendmentView hole={hole} ratified={ratified.includes(hole.id)} onRatify={() => setRatified((r) => [...r, hole.id])} />;
  else if (section === "holes" && hole) page = <HoleView hole={hole} ratified={ratified.includes(hole.id)} />;
  else if (section === "bench") page = <Bench />;
  else page = <Audit onDone={(r) => { setReport(r); setRatified([]); }} />;

  const nav = [
    { href: "#/", icon: PlayCircle, label: "Audit", on: !section || section.startsWith("?") },
    { href: "#/report", icon: FileWarning, label: "Report", on: section === "report" || section === "holes", count: report.holes.length - ratified.length },
    { href: "#/bench", icon: Gauge, label: "Bench", on: section === "bench" },
  ];

  return (
    <div className="shell">
      {/* The hash is the router, so the skip link moves focus itself. */}
      <a className="skip" href="#/" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <aside className="rail">
        <a className="lockup" href="#/" aria-label="Bylaw home">
          <Logo />
          <b>bylaw</b>
        </a>
        <nav className="nav" aria-label="Main">
          {nav.map((n) => (
            <a key={n.href} href={n.href} aria-current={n.on ? "page" : undefined}>
              <n.icon size={17} aria-hidden="true" />
              {n.label}
              {!!n.count && <span className="count" aria-label={`${n.count} open holes`}>{n.count}</span>}
            </a>
          ))}
        </nav>
        <div className="rail-foot">
          <div className="meter" aria-label="Muse Spark usage for the last run">
            <span className="k"><Sparkles size={12} aria-hidden="true" />Muse Spark tokens</span>
            <span className="v">{int(report.stats.tokens)}</span>
            <span className="s">{report.stats.llm_calls} calls · {report.run.domain}</span>
          </div>
          <span className="proto"><FlaskConical size={11} aria-hidden="true" /> Prototype on fixture data</span>
        </div>
      </aside>
      <main className="main" id="main" tabIndex={-1}>{page}</main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
