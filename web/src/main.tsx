import { StrictMode, useEffect, useRef, useState, type KeyboardEvent as KeyEv } from "react";
import { createRoot } from "react-dom/client";
import { Database, FileWarning, Gauge, Moon, PanelLeftClose, PanelLeftOpen, PlayCircle, Radio, Search, Sun, type LucideIcon } from "lucide-react";
import { DOMAINS, DOMAIN_NAME, api, useGet, type Domain, type Report } from "./api";
import { Logo, Ticker, when } from "./ui";
import { Audit } from "./screens/Audit";
import { ReportView } from "./screens/Report";
import { HoleView } from "./screens/Hole";
import { AmendmentView } from "./screens/Amendment";
import { Bench } from "./screens/Bench";
import { Live } from "./screens/Live";
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

// index.html sets data-theme before the first paint, from the stored choice or the system preference.
const THEME = "bylaw.theme";
const useTheme = () => {
  const [t, set] = useState(() => document.documentElement.dataset.theme === "light" ? "light" : "dark");
  const flip = () => {
    const n = t === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = n;
    try { localStorage.setItem(THEME, n); } catch { /* storage blocked: this session only */ }
    set(n);
  };
  return [t, flip] as const;
};

// Routes: #/ (audit), #/<domain>/report, #/<domain>/holes/<key>[/amendment], #/<domain>/bench, #/live
// ?film=1 (before the hash) hides the rail and the player chrome, for the recording.
const FILM = new URLSearchParams(location.search).get("film") === "1";
function App() {
  const path = useHash();
  const [, seg, section, rawKey, sub] = path.split("/");
  const inUrl = DOMAINS.includes(seg as Domain) ? (seg as Domain) : undefined;
  const [last, setLast] = useState<Domain>("airline");
  useEffect(() => void (inUrl && setLast(inUrl)), [inUrl]);
  const domain = inUrl ?? last;
  const key = rawKey ? decodeURIComponent(rawKey) : "";
  const report = useGet<Report>(api.report(domain));
  const [collapsed, toggle] = useCollapsed();
  const [theme, flip] = useTheme();
  const [palette, setPalette] = useState(false);
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette((p) => !p);
      }
    };
    addEventListener("keydown", on);
    return () => removeEventListener("keydown", on);
  }, []);

  let page;
  if (seg === "live") page = <Live film={FILM} />;
  else if (inUrl && section === "report") page = <ReportView domain={domain} report={report} />;
  else if (inUrl && section === "holes" && key && sub === "amendment") page = <AmendmentView domain={domain} hkey={key} effort={report.data?.run.effort} />;
  else if (inUrl && section === "holes" && key) page = <HoleView domain={domain} hkey={key} muse={report.data?.run.mode === "muse"} />;
  else if (inUrl && section === "bench") page = <Bench domain={domain} />;
  else page = <Audit domain={domain} onDomain={setLast} onDone={report.reload} />;

  const r = report.data;
  const nA = r?.holes.length ?? 0, nB = r?.contradictions?.length ?? 0;
  const nav: { href: string; icon: LucideIcon; label: string; on: boolean; count?: number; red?: boolean }[] = [
    { href: "#/", icon: PlayCircle, label: "Audit", on: !inUrl && seg !== "live" },
    { href: `#/${domain}/report`, icon: FileWarning, label: "Report", on: section === "report" || section === "holes", count: nA || nB, red: nA > 0 },
    { href: `#/${domain}/bench`, icon: Gauge, label: "Bench", on: section === "bench" },
    { href: "#/live", icon: Radio, label: "Live", on: seg === "live" },
  ];

  return (
    <div className={(collapsed ? "shell collapsed" : "shell") + (FILM && seg === "live" ? " film" : "")}>
      {/* The hash is the router, so the skip link moves focus itself. */}
      <a className="skip" href="#/" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <div className="routebar" key={path} aria-hidden="true" />
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
        <button className="jump" onClick={() => setPalette(true)} data-tip={collapsed ? "Jump to  ⌘K" : undefined} aria-label="Jump to a screen or action" aria-keyshortcuts="Meta+K Control+K">
          <Search size={15} aria-hidden="true" /><span className="lbl">Jump to…</span><kbd>⌘K</kbd>
        </button>
        <nav className="nav" aria-label="Main">
          {nav.map((n) => (
            <a key={n.label} href={n.href} aria-current={n.on ? "page" : undefined} data-tip={collapsed ? (n.count ? `${n.label}  ${n.count}` : n.label) : undefined}>
              <n.icon size={17} aria-hidden="true" />
              <span className="lbl">{n.label}</span>
              {!!n.count && <span className={n.red ? "count r" : "count"} aria-label={n.red ? `${n.count} proven holes` : `${n.count} contradictions`}>{n.count}</span>}
            </a>
          ))}
        </nav>
        <div className="rail-foot">
          {r && (
            <div className="meter" aria-label={`Muse Spark usage in the latest ${DOMAIN_NAME[domain]} report`}>
              <span className="k">Muse Spark tokens</span>
              <Ticker className="v" value={r.stats.tokens} />
              <span className="s">
                {r.run.mode === "bfs-fallback" ? "Muse unavailable, ran offline" : r.stats.llm_calls ? `${r.stats.llm_calls} calls${r.run.model ? `, ${r.run.model}` : ""}` : "offline run, no Muse calls"}
              </span>
            </div>
          )}
          <span className="source" data-testid="data-source">
            <Database size={11} aria-hidden="true" />
            <span>{report.loading ? "Loading latest report…" : r ? `${DOMAIN_NAME[domain]} report, ${when(r.run.started)}${r.run.commit ? `, ${r.run.commit.slice(0, 7)}` : ""}` : report.error?.status === 404 ? `No ${DOMAIN_NAME[domain]} report yet` : "API not reachable"}</span>
          </span>
          <button className="theme-t" onClick={flip} aria-label={theme === "light" ? "Switch to dark theme" : "Switch to light theme"} data-tip={collapsed ? (theme === "light" ? "Dark theme" : "Light theme") : undefined}>
            {theme === "light" ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
            <span className="lbl">{theme === "light" ? "Dark theme" : "Light theme"}</span>
          </button>
        </div>
      </aside>
      <main className="main" id="main" tabIndex={-1}>
        <div key={path} style={{ display: "contents" }}>{page}</div>
      </main>
      {palette && <Palette domain={domain} collapsed={collapsed} onToggle={toggle} onTheme={flip} theme={theme} onClose={() => setPalette(false)} />}
    </div>
  );
}

// ⌘K: jump to a screen or run a view action. A native <dialog>, so focus and Escape come with it.
function Palette({ domain, collapsed, theme, onToggle, onTheme, onClose }: {
  domain: Domain; collapsed: boolean; theme: string; onToggle: () => void; onTheme: () => void; onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const go = (h: string) => () => { location.hash = h; };
  const items = [
    { label: "Run an audit", icon: PlayCircle, hint: "Audit", run: go("#/") },
    { label: `Open the ${DOMAIN_NAME[domain]} report`, icon: FileWarning, hint: "Report", run: go(`#/${domain}/report`) },
    { label: "Compare Muse with blind BFS", icon: Gauge, hint: "Bench", run: go(`#/${domain}/bench`) },
    { label: "Watch the live run", icon: Radio, hint: "Live", run: go("#/live") },
    ...DOMAINS.filter((d) => d !== domain).map((d) => ({ label: `Switch to ${DOMAIN_NAME[d]}`, icon: Database, hint: "Domain", run: go(`#/${d}/report`) })),
    { label: collapsed ? "Expand the sidebar" : "Collapse the sidebar", icon: collapsed ? PanelLeftOpen : PanelLeftClose, hint: "View", run: onToggle },
    { label: theme === "light" ? "Use the dark theme" : "Use the light theme", icon: theme === "light" ? Moon : Sun, hint: "View", run: onTheme },
  ].filter((i) => (i.label + " " + i.hint).toLowerCase().includes(q.trim().toLowerCase()));
  useEffect(() => { if (!ref.current?.open) ref.current?.showModal(); }, []);
  useEffect(() => setSel(0), [q]);
  const pick = (i: number) => {
    items[i]?.run();
    ref.current?.close();
  };
  const key = (e: KeyEv) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(items.length - 1, s + 1)); }
    if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(0, s - 1)); }
    if (e.key === "Enter") { e.preventDefault(); pick(sel); }
  };
  return (
    <dialog ref={ref} className="palette" aria-label="Jump to" onClose={onClose} onClick={(e) => e.target === ref.current && ref.current.close()}>
      <div className="q">
        <Search aria-hidden="true" />
        <input autoFocus placeholder="Search screens and actions…" aria-label="Search screens and actions" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={key}
          autoComplete="off" spellCheck={false} role="combobox" aria-expanded="true" aria-controls="pal-list" aria-activedescendant={items.length ? `pal-${sel}` : undefined} />
      </div>
      {items.length ? (
        <ul id="pal-list" role="listbox">
          {items.map((it, i) => (
            <li key={it.label} role="presentation">
              <button id={`pal-${i}`} role="option" aria-selected={i === sel} tabIndex={-1} onMouseEnter={() => setSel(i)} onClick={() => pick(i)}>
                <it.icon aria-hidden="true" />{it.label}<span className="hint">{it.hint}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : <p className="none">Nothing matches “{q}”.</p>}
      <div className="foot"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>↵</kbd> open</span><span><kbd>esc</kbd> close</span></div>
    </dialog>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
