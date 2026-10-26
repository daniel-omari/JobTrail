import { useEffect, useState } from "react";
import { api, STATUSES, type Fields, type QuarantineItem, type Status } from "../api";
import { EmptyState } from "../components/EmptyState";
import { StageBadge } from "../components/StageBadge";
import { useScan } from "../scan-context";
import "./Quarantine.css";

function ReleaseForm({ item, onDone, onCancel }: { item: QuarantineItem; onDone: () => void; onCancel: () => void }) {
  const p = item.rules_prefill;
  const [f, setF] = useState<Fields>({ company: p.company ?? "", role: p.role ?? "", status: (p.status ?? "Applied") as Status });
  const [error, setError] = useState<string | null>(null);
  const save = async () => {
    try { await api.release(item.id, f); onDone(); } catch { setError("Please fill in company and role."); }
  };
  return (
    <div className="release">
      <p className="small muted">Pre-filled from JobTrail's rules, <strong>not</strong> from the AI's answer. Check it before saving.</p>
      <div className="form-row">
        <label>Company<input value={f.company} onChange={(e) => setF({ ...f, company: e.target.value })} /></label>
        <label>Role<input value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} /></label>
        <label>Stage<select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value as Status })}>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select></label>
      </div>
      {error && <p className="small" style={{ color: "var(--rejected)" }}>{error}</p>}
      <div className="row-actions">
        <button className="btn btn-primary" onClick={save}>Save to Tracker</button>
        <button className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export function Quarantine() {
  const { version, refresh } = useScan();
  const [items, setItems] = useState<QuarantineItem[] | null>(null);
  const [releasing, setReleasing] = useState<number | null>(null);
  useEffect(() => { api.quarantine().then(setItems); }, [version]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Quarantine</h1>
          <p className="muted">Emails that looked like they were trying to manipulate JobTrail or its AI. Nothing from them reached your tracker.</p>
        </div>
      </div>
      {items && items.length === 0 && <div className="card"><EmptyState title="No threats detected"><p>Suspicious emails will appear here with the reason they were stopped.</p></EmptyState></div>}
      {items?.map((q) => (
        <div className="card q-card" key={q.id}>
          <div className="q-head">
            <div>
              <div className="q-subject">{q.subject}</div>
              <div className="small muted">{q.sender} · {new Date(q.received_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</div>
            </div>
            <span className="badge badge-rejected">Quarantined</span>
          </div>
          <div className="q-affects">
            {q.affects ? (
              <>This email was about <strong>{q.affects.company} · {q.affects.role}</strong> in your Tracker. It still shows{" "}
                <StageBadge status={q.affects.current_status} />, because <strong>nothing was changed</strong>.</>
            ) : (
              <>It doesn't match any application in your Tracker, and <strong>nothing was added</strong>.</>
            )}
          </div>
          {q.reasons.map((r, i) => (
            <div className="q-reason" key={i}>
              <div className="q-reason-title">{r.reason}</div>
              {r.excerpt && <blockquote className="q-excerpt">{r.excerpt}</blockquote>}
              <p className="q-info"><strong>Info:</strong> {r.info}</p>
            </div>
          ))}
          {releasing === q.id ? (
            <ReleaseForm item={q} onCancel={() => setReleasing(null)} onDone={() => { setReleasing(null); refresh(); }} />
          ) : (
            <div className="row-actions">
              <button className="btn" onClick={() => setReleasing(q.id)}>Release…</button>
              <button className="btn btn-danger" onClick={async () => { await api.discard(q.id); refresh(); }}>Discard</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
