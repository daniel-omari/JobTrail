import { NavLink } from "react-router";
import { useScan } from "../scan-context";
import { Tooltip } from "./Tooltip";
import "./NavBar.css";

const LINKS = [
  { to: "/", label: "Overview" },
  { to: "/tracker", label: "Tracker" },
  { to: "/review", label: "Review", badge: "review" as const },
  { to: "/quarantine", label: "Quarantine", badge: "quarantine" as const },
  { to: "/privacy", label: "Privacy" },
  { to: "/export", label: "Export" },
  { to: "/settings", label: "Settings" },
];

export function NavBar() {
  const { scan, scanning, status } = useScan();
  const count = (b?: "review" | "quarantine") =>
    b === "review" ? status?.review_count ?? 0 : b === "quarantine" ? status?.quarantine_count ?? 0 : 0;
  return (
    <header className="nav">
      <div className="nav-inner">
        <NavLink to="/" className="brand" aria-label="JobTrail home">
          <span className="brand-mark" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 14 14"><path d="M2 10 L6 6 L8 8 L12 3" stroke="#fff" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
          </span>
          JobTrail
          {status?.demo && <span className="demo-pill" title="Started with --demo: separate demo data and demo-only controls">DEMO</span>}
        </NavLink>
        <nav className="nav-links">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
              {l.label}
              {count(l.badge) > 0 && <span className={`count ${l.badge === "review" ? "count-review" : ""}`}>{count(l.badge)}</span>}
            </NavLink>
          ))}
        </nav>
        <Tooltip text="Checks your email headers for job-application updates. Only emails from recruiting platforms (or senders you approve) are opened; everything else is skipped unread.">
          <button className="btn btn-primary" onClick={scan} disabled={scanning}>{scanning ? "Scanning…" : "Scan Now"}</button>
        </Tooltip>
      </div>
    </header>
  );
}
