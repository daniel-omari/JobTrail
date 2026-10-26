import { useEffect, useMemo, useState } from "react";
import { api, STATUSES, type Application, type Status } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { EmptyState } from "../components/EmptyState";
import { StageBadge } from "../components/StageBadge";
import { useScan } from "../scan-context";
import "./Tracker.css";

const fmt = (d: string | null) => (d ? new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—");
const RULE_LABEL: Record<string, string> = {
  known_platform: "known recruiting platform",
  trusted_sender: "sender you approved",
  approved_by_you: "you approved it in Review",
};
const today = () => new Date().toISOString().slice(0, 10);

interface FormValues { company: string; role: string; status: Status; date: string; how_applied: string; notes: string }

function AppForm({ initial, submitLabel, showDate, onSubmit, onCancel }: {
  initial: FormValues; submitLabel: string; showDate: boolean;
  onSubmit: (v: FormValues) => Promise<void>; onCancel: () => void;
}) {
  const [v, setV] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const submit = async () => {
    if (!v.company.trim() || !v.role.trim()) { setError("Company and role are required."); return; }
    try { await onSubmit(v); } catch { setError("Couldn't save. Check the fields and try again."); }
  };
  return (
    <div className="app-form">
      <label>Company<input value={v.company} onChange={(e) => setV({ ...v, company: e.target.value })} /></label>
      <label>Role<input value={v.role} onChange={(e) => setV({ ...v, role: e.target.value })} /></label>
      <label>Stage<select value={v.status} onChange={(e) => setV({ ...v, status: e.target.value as Status })}>
        {STATUSES.map((s) => <option key={s}>{s}</option>)}
      </select></label>
      {showDate && <label>Date<input type="date" value={v.date} max={today()} onChange={(e) => setV({ ...v, date: e.target.value })} /></label>}
      <label>How applied<input value={v.how_applied} onChange={(e) => setV({ ...v, how_applied: e.target.value })} /></label>
      <label className="notes-field">Notes <span className="hint">only for you, never included in the export</span>
        <textarea rows={3} maxLength={1000} value={v.notes} placeholder="e.g. Interview Thu 2pm, ask about hybrid working"
          onChange={(e) => setV({ ...v, notes: e.target.value })} />
      </label>
      {error && <p className="form-error">{error}</p>}
      <div className="row-actions">
        <button className="btn btn-primary" onClick={submit}>{submitLabel}</button>
        <button className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function Drawer({ app, onClose, onChanged }: { app: Application; onClose: () => void; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [confirm, setConfirm] = useState<"delete" | "dnt" | null>(null);
  return (
    <aside className="drawer" aria-label={`${app.company} details`}>
      <div className="drawer-head">
        <div>
          <div className="drawer-title">{app.company}</div>
          <div className="muted">{app.role}</div>
        </div>
        <button className="btn" onClick={onClose} aria-label="Close details">✕</button>
      </div>
      <div style={{ margin: "12px 0" }}><StageBadge status={app.current_status} /></div>
      <dl className="facts">
        <dt>How applied</dt><dd>{app.how_applied}</dd>
        <dt>Source</dt><dd>{app.manual ? "Added manually" : app.source}</dd>
      </dl>
      {app.notes && !editing && <div className="notes"><div className="notes-label">Notes</div>{app.notes}</div>}
      <h2>History</h2>
      <p className="small muted" style={{ marginTop: -6 }}>Each stage and the email it came from. Only the subject is shown, because JobTrail never stores email text.</p>
      <ol className="timeline">
        {app.history.map((h, i) => (
          <li key={i}>
            <span className={`tl-dot tl-${h.status}`} />
            <div>
              <div><strong>{h.status}</strong><span className="muted"> · {fmt(h.event_date)}</span></div>
              <div className="tl-source">
                {h.source === "email" && <>✉ “{h.subject}”{h.rule && <span className="muted"> · opened because: {RULE_LABEL[h.rule] ?? h.rule}</span>}</>}
                {h.source === "manual" && <span className="muted">Added or changed by you</span>}
                {h.source === "redacted" && <span className="muted">Email details redacted</span>}
              </div>
            </div>
          </li>
        ))}
      </ol>
      {editing ? (
        <AppForm
          showDate={false} submitLabel="Save changes"
          initial={{ company: app.company, role: app.role, status: app.current_status, date: today(), how_applied: app.how_applied, notes: app.notes }}
          onCancel={() => setEditing(false)}
          onSubmit={async (v) => { await api.editApplication(app.id, { company: v.company, role: v.role, status: v.status, how_applied: v.how_applied, notes: v.notes }); setEditing(false); onChanged(); }}
        />
      ) : (
        <div className="row-actions wrap">
          <button className="btn" onClick={() => setEditing(true)}>Edit</button>
          {app.archived && <button className="btn" onClick={async () => { await api.restore(app.id); onChanged(); }}>Restore to Tracker</button>}
          <button className="btn" onClick={() => setConfirm("dnt")}>Don't track this</button>
          <button className="btn btn-danger" onClick={() => setConfirm("delete")}>Delete</button>
        </div>
      )}
      <ConfirmDialog
        open={confirm !== null} danger
        title={confirm === "dnt" ? "Stop tracking this application?" : "Delete this application?"}
        confirmLabel={confirm === "dnt" ? "Don't track this" : "Delete"}
        onCancel={() => setConfirm(null)}
        onConfirm={async () => {
          if (confirm === "dnt") await api.doNotTrack(app.id); else await api.deleteApplication(app.id);
          setConfirm(null); onClose(); onChanged();
        }}
      >
        {confirm === "dnt"
          ? <>It will be removed, and future emails about <strong>{app.company} – {app.role}</strong> will be skipped without being opened.</>
          : <>It will be removed from JobTrail. Its access-ledger lines keep only the date and the reason they were opened.</>}
      </ConfirmDialog>
    </aside>
  );
}

function AppTable({ apps, onOpen }: { apps: Application[]; onOpen: (a: Application) => void }) {
  return (
    <table className="data clickable">
      <thead><tr><th>Company</th><th>Role</th><th>Stage</th><th>Applied</th><th>Last update</th><th>How applied</th></tr></thead>
      <tbody>
        {apps.map((a) => (
          <tr key={a.id} onClick={() => onOpen(a)} tabIndex={0} onKeyDown={(e) => e.key === "Enter" && onOpen(a)}>
            <td><strong>{a.company}</strong>{a.manual && <span className="badge badge-neutral manual">manual</span>}{a.notes && <span className="has-notes" title={a.notes} aria-label="Has notes">✎</span>}</td>
            <td>{a.role}</td>
            <td><StageBadge status={a.current_status} /></td>
            <td className="muted small">{fmt(a.applied_date)}</td>
            <td className="muted small">{fmt(a.last_update)}</td>
            <td className="muted small">{a.how_applied}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Tracker() {
  const { version, refresh } = useScan();
  const [active, setActive] = useState<Application[] | null>(null);
  const [archived, setArchived] = useState<Application[]>([]);
  const [openId, setOpenId] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [olderThan, setOlderThan] = useState(7);
  const [forceConfirm, setForceConfirm] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.applications(false).then(setActive);
    api.applications(true).then(setArchived);
  }, [version]);

  const open = [...(active ?? []), ...archived].find((a) => a.id === openId) ?? null;

  const q = query.trim().toLowerCase();
  const matches = (a: Application) => !q || `${a.company} ${a.role} ${a.notes}`.toLowerCase().includes(q);
  const shownActive = (active ?? []).filter(matches);
  const shownArchived = archived.filter(matches);

  // Archive: newest first, grouped by month of last update.
  const months = useMemo(() => {
    const groups = new Map<string, Application[]>();
    for (const a of [...shownArchived].sort((x, y) => (y.last_update ?? "").localeCompare(x.last_update ?? ""))) {
      const key = a.last_update ? new Date(a.last_update).toLocaleDateString("en-GB", { month: "long", year: "numeric" }) : "Undated";
      groups.set(key, [...(groups.get(key) ?? []), a]);
    }
    return [...groups.entries()];
  }, [shownArchived]);

  const clear = async () => {
    const { removed } = await api.clearArchive(olderThan);
    setNote(removed ? `Cleared ${removed} entr${removed === 1 ? "y" : "ies"} older than ${olderThan} days.` : `Nothing older than ${olderThan} days to clear.`);
    refresh();
  };

  return (
    <div className="page tracker">
      <div className="page-head">
        <div><h1>Tracker</h1><p className="muted">Every application JobTrail found, and where it stands. Click a row for details.</p></div>
        <div className="row-actions">
          <input className="search" type="search" placeholder="Search company, role or notes" value={query}
            onChange={(e) => setQuery(e.target.value)} aria-label="Search applications" />
          <button className="btn btn-primary" onClick={() => setAdding(true)}>Add entry</button>
        </div>
      </div>

      {adding && (
        <div className="card">
          <h2>Add an application</h2>
          <p className="small muted">For anything JobTrail missed, like an application made by phone or in person.</p>
          <AppForm
            showDate submitLabel="Add to Tracker"
            initial={{ company: "", role: "", status: "Applied", date: today(), how_applied: "Added manually", notes: "" }}
            onCancel={() => setAdding(false)}
            onSubmit={async (v) => { await api.addApplication(v); setAdding(false); refresh(); }}
          />
        </div>
      )}

      <div className="card">
        <h2>Active applications</h2>
        {active && active.length === 0
          ? <EmptyState title="No active applications yet"><p>Run a scan, or add one manually.</p></EmptyState>
          : active && (shownActive.length === 0
            ? <p className="muted">No active applications match “{query}”.</p>
            : <AppTable apps={shownActive} onOpen={(a) => setOpenId(a.id)} />)}
      </div>

      <div className="card">
        <div className="archive-head">
          <div>
            <h2>Rejected / No Response</h2>
            <p className="small muted">Newest first. Normal clearing always keeps the last 7 days, so this week's UC export stays complete.</p>
          </div>
          <div className="row-actions wrap">
            <select value={olderThan} onChange={(e) => setOlderThan(Number(e.target.value))} aria-label="Clear entries older than">
              <option value={7}>Older than 1 week</option>
              <option value={30}>Older than 30 days</option>
              <option value={90}>Older than 90 days</option>
            </select>
            <button className="btn" onClick={clear} disabled={archived.length === 0}>Clear</button>
            <button className="btn btn-danger" onClick={() => setForceConfirm(true)} disabled={archived.length === 0}>Force Clean</button>
          </div>
        </div>
        {note && <p className="small" role="status">{note}</p>}
        {archived.length === 0 ? <p className="muted">Nothing here.</p>
          : shownArchived.length === 0 ? <p className="muted">Nothing here matches “{query}”.</p> : months.map(([month, apps]) => (
          <div key={month} className="month">
            <div className="month-label">{month}</div>
            <AppTable apps={apps} onOpen={(a) => setOpenId(a.id)} />
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={forceConfirm} danger title="Force clean the whole list?" confirmLabel="Force Clean"
        onCancel={() => setForceConfirm(false)}
        onConfirm={async () => { const { removed } = await api.forceClean(); setForceConfirm(false); setNote(`Removed ${removed} entries.`); refresh(); }}
      >
        This also removes rejections from <strong>the last 7 days</strong>. They will disappear from this week's UC journal export, so export first if you need them.
      </ConfirmDialog>

      {open && <><div className="scrim" onClick={() => setOpenId(null)} /><Drawer app={open} onClose={() => setOpenId(null)} onChanged={refresh} /></>}
    </div>
  );
}
