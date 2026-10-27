import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { Database, FileWarning, Gauge, PanelLeftClose, PanelLeftOpen, PlayCircle, Sparkles } from "lucide-react";
import { DOMAINS, api, useGet, type Domain, type Report } from "./api";
import { Logo, int, when } from "./ui";
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

const COLLAPSED = "bylaw.sidebar.collapsed";
const useCollapsed = () => {
  const [c, set] = useState(() => {
    try { return localStorage.getItem(COLLAPSED) === "1"; } catch { return false; }
  });
  const toggle = () => set((v) => {
    try { localStorage.setItem(COLLAPSED, v ? "0" : "1"); } catch { /* storage blocked: keep it in memory */ }
    return !v;
  });
  return [c, toggle] as const;
};

// Routes: #/ (audit), #/<domain>/report, #/<domain>/holes/<key>[/amendment], #/<domain>/bench
function App() {
  const path = useHash();
  const [, seg, section, rawKey, sub] = path.split("/");
  const inUrl = DOMAINS.includes(seg as Domain) ? (seg as Domain) : undefined;
  const [last, setLast] = useState<Domain>("airline");
  useEffect(() => void (inUrl && setLast(inUrl)), [inUrl]);
  const domain = inUrl ?? last;
  const key = rawKey ? decodeURIComponent(rawKey) : "";
  const report = useGet<Report>(api.report(domain));

  let page;
  if (inUrl && section === "report") page = <ReportView domain={domain} report={report} />;
  else if (inUrl && section === "holes" && key && sub === "amendment") page = <AmendmentView domain={domain} hkey={key} />;
  else if (inUrl && section === "holes" && key) page = <HoleView domain={domain} hkey={key} muse={report.data?.run.mode === "muse"} />;
  else if (inUrl && section === "bench") page = <Bench domain={domain} />;
  else page = <Audit domain={domain} onDomain={setLast} onDone={report.reload} />;

  const nav = [
    { href: "#/", icon: PlayCircle, label: "Audit", on: !inUrl },
    { href: `#/${domain}/report`, icon: FileWarning, label: "Report", on: section === "report" || section === "holes", count: report.data?.holes.length },
    { href: `#/${domain}/bench`, icon: Gauge, label: "Bench", on: section === "bench" },
  ];
  const r = report.data;
  const [collapsed, toggle] = useCollapsed();

  return (
    <div className={collapsed ? "shell collapsed" : "shell"}>
      {/* The hash is the router, so the skip link moves focus itself. */}
      <a className="skip" href="#/" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <aside className="rail">
        <div className="rail-head">
          <a className="lockup" href="#/" aria-label="Bylaw home">
            <Logo />
            <b>bylaw</b>
          </a>
          {/* Collapsed, the button sits over the logo and shows itself on hover or keyboard focus. */}
          <button className="rail-toggle" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} onClick={toggle}>
            {collapsed ? <PanelLeftOpen size={18} aria-hidden="true" /> : <PanelLeftClose size={18} aria-hidden="true" />}
          </button>
        </div>
        <nav className="nav" aria-label="Main">
          {nav.map((n) => (
            <a key={n.label} href={n.href} aria-current={n.on ? "page" : undefined} title={collapsed ? n.label : undefined}>
              <n.icon size={17} aria-hidden="true" />
              <span className="lbl">{n.label}</span>
              {!!n.count && <span className="count" aria-label={`${n.count} proven holes`}>{n.count}</span>}
            </a>
          ))}
        </nav>
        <div className="rail-foot">
          {r && (
            <div className="meter" aria-label={`Muse Spark usage in the latest ${domain} report`}>
              <span className="k"><Sparkles size={12} aria-hidden="true" />Muse Spark tokens</span>
              <span className="v">{int(r.stats.tokens)}</span>
              <span className="s">{r.stats.llm_calls ? `${r.stats.llm_calls} calls · ${r.run.model || "muse"}` : "offline run, no Muse calls"}</span>
            </div>
          )}
          <span className="proto" data-testid="data-source">
            <Database size={11} aria-hidden="true" />{" "}
            {report.loading ? "Loading latest report…" : r ? `${domain} report · ${when(r.run.started)}${r.run.commit ? ` · ${r.run.commit.slice(0, 7)}` : ""}` : report.error?.status === 404 ? `No ${domain} report yet` : "API not reachable"}
          </span>
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
