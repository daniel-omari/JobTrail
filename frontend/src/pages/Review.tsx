import { useEffect, useState } from "react";
import { api, type ReviewItem } from "../api";
import { EmptyState } from "../components/EmptyState";
import { useScan } from "../scan-context";

const OUTCOME: Record<string, string> = {
  tracked: "Added to your Tracker.",
  quarantined: "Opened, but it looked suspicious, so it went to Quarantine.",
  unreadable: "Opened, but no application details could be found. Nothing was stored.",
  rejected: "Rejected. It was never opened, and this sender won't be offered again.",
  gone: "That email is no longer in the inbox.",
};

export function Review() {
  const { version, refresh } = useScan();
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => { api.review().then(setItems); }, [version]);

  const act = async (id: number, fn: (id: number) => Promise<{ outcome: string }>) => {
    setBusy(id);
    try { setNote(OUTCOME[(await fn(id)).outcome] ?? null); refresh(); } finally { setBusy(null); }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Review</h1>
          <p className="muted">
            These emails come from senders JobTrail doesn't know, but their subjects look job-related.
            <strong> None of them has been opened.</strong> You only see the sender, subject and date.
          </p>
        </div>
      </div>
      {note && <div className="card small" role="status">{note}</div>}
      <div className="card">
        {items && items.length === 0 ? (
          <EmptyState title="Nothing to review"><p>Emails from unknown senders that look job-related will wait here for you.</p></EmptyState>
        ) : (
          <table className="data">
            <thead><tr><th>Sender</th><th>Subject</th><th>Received</th><th></th></tr></thead>
            <tbody>
              {items?.map((r) => (
                <tr key={r.id}>
                  <td className="small">{r.sender}</td>
                  <td><strong>{r.subject}</strong></td>
                  <td className="muted small">{new Date(r.received_date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</td>
                  <td style={{ whiteSpace: "nowrap", textAlign: "right" }}>
                    <button className="btn btn-primary" disabled={busy === r.id} onClick={() => act(r.id, api.approve)} title="Let JobTrail read this email and trust this sender in future">Approve</button>{" "}
                    <button className="btn" disabled={busy === r.id} onClick={() => act(r.id, api.reject)} title="Never open it, and don't ask about this sender again">Reject</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="small muted" style={{ marginTop: 12 }}>
          <strong>Approve</strong> lets JobTrail read that one email and trust the sender for future scans. <strong>Reject</strong> means it's never opened, and the sender isn't offered again.
        </p>
      </div>
    </div>
  );
}
