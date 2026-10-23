import { useEffect, useState, type ReactNode } from "react";
import { api, type Everything } from "../api";
import { useScan } from "../scan-context";

function Group({ title, count, children }: { title: string; count: number | string; children: ReactNode }) {
  return (
    <details className="held">
      <summary><span>{title}</span><span className="held-count">{count}</span></summary>
      <div className="held-body">{children}</div>
    </details>
  );
}

const list = (items: string[]) => (items.length ? <ul>{items.map((i) => <li key={i}>{i}</li>)}</ul> : <p className="muted small">None.</p>);

export function HeldData() {
  const { version } = useScan();
  const [d, setD] = useState<Everything | null>(null);
  useEffect(() => { api.everything().then(setD); }, [version]);
  if (!d) return null;

  const download = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(d, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url; a.download = "jobtrail-everything.json"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="card">
      <div className="held-head">
        <div>
          <h2>Everything JobTrail holds about you</h2>
          <p className="small muted">This is the complete list. It's all stored in one file on this computer, and nothing is kept anywhere else.</p>
        </div>
        <button className="btn" onClick={download}>Download a copy (JSON)</button>
      </div>
      <Group title="Applications" count={d.applications.length}>
        {list(d.applications.map((a) => `${a.company} · ${a.role} · ${a.current_status} (${a.history.length} event${a.history.length === 1 ? "" : "s"})`))}
      </Group>
      <Group title="Access ledger lines" count={d.ledger.length}>
        {list(d.ledger.map((e) => e.redacted ? `${e.opened_at.slice(0, 10)} · ${e.rule} · (redacted)` : `${e.opened_at.slice(0, 10)} · ${e.sender} · ${e.subject}`))}
      </Group>
      <Group title="Waiting for review (sender + subject only)" count={d.review_queue.length}>
        {list(d.review_queue.map((r) => `${r.sender} · ${r.subject}`))}
      </Group>
      <Group title="Quarantined (sender, subject, short excerpt)" count={d.quarantine.length}>
        {list(d.quarantine.map((q) => `${q.sender} · ${q.subject}`))}
      </Group>
      <Group title="Senders you approved / rejected" count={`${d.trusted_senders.length} / ${d.rejected_senders.length}`}>
        {list([...d.trusted_senders.map((s) => `Approved: ${s}`), ...d.rejected_senders.map((s) => `Rejected: ${s}`)])}
      </Group>
      <Group title="Don't-track list" count={d.do_not_track.length}>
        {list(d.do_not_track.map((x) => `${x.company} · ${x.role}`))}
      </Group>
      <Group title="Processed-email fingerprints" count={d.processed_email_fingerprints}>
        <p className="small">One-way hashes of email IDs already handled, so they aren't read again. They contain no sender, subject or content.</p>
      </Group>
      <Group title="Scan history (counts only)" count={d.scan_runs.length}>
        {list(d.scan_runs.map((r) => `${new Date(r.ran_at).toLocaleString("en-GB")} · checked ${r.checked}, opened ${r.opened}, skipped ${r.skipped}`))}
      </Group>
      <Group title="Settings" count="—">
        <pre className="small">{JSON.stringify(d.settings, null, 2)}</pre>
      </Group>
      <p className="small muted" style={{ marginTop: 12 }}>Raw email text is never stored. Emails that were skipped are only counted, never listed.</p>
    </div>
  );
}
