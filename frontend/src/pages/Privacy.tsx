import { useEffect, useState } from "react";
import { api, type LedgerResponse } from "../api";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { EmptyState } from "../components/EmptyState";
import { useScan } from "../scan-context";

const RULES: Record<string, string> = {
  known_platform: "Known recruiting platform",
  trusted_sender: "Sender you approved",
};

export function Privacy() {
  const { version, refresh } = useScan();
  const [data, setData] = useState<LedgerResponse | null>(null);
  const [confirming, setConfirming] = useState(false);
  useEffect(() => { api.ledger().then(setData); }, [version]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Privacy</h1>
          <p className="muted">Every email JobTrail opened, why it opened it, and exactly what it kept. Everything else is skipped without being read.</p>
        </div>
        <button className="btn btn-danger" onClick={() => setConfirming(true)}>Delete all</button>
      </div>
      <ConfirmDialog
        open={confirming} title="Delete everything JobTrail holds?" confirmLabel="Delete all" danger
        onCancel={() => setConfirming(false)}
        onConfirm={async () => { await api.deleteAll(); setConfirming(false); refresh(); }}
      >
        This permanently removes every application, the access ledger, review and quarantine items, and your settings from this computer. It can't be undone.
      </ConfirmDialog>
      {data && (
        <div className="card">
          <h2>Access ledger</h2>
          <p className="muted small">
            {data.entries.length} email{data.entries.length === 1 ? "" : "s"} opened · {data.skipped_unopened_total} skipped unopened across all scans.
            Raw email text is never stored.
          </p>
          {data.entries.length === 0 ? (
            <EmptyState title="Nothing opened yet"><p>Run a scan and each opened email will be listed here.</p></EmptyState>
          ) : (
            <table className="data">
              <thead><tr><th>Opened</th><th>Sender</th><th>Subject</th><th>Why</th><th>What was stored</th></tr></thead>
              <tbody>
                {data.entries.map((e) => (
                  <tr key={e.id}>
                    <td className="muted small">{new Date(e.opened_at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</td>
                    <td className="small">{e.redacted ? <em className="muted">redacted</em> : e.sender}</td>
                    <td className="small">{e.redacted ? <em className="muted">redacted</em> : e.subject}</td>
                    <td className="small">{RULES[e.rule] ?? e.rule}</td>
                    <td className="small"><code>{e.stored_summary}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
