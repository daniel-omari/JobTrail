import { useScan } from "../scan-context";

export function ScanToast() {
  const { lastSummary: s, dismissSummary } = useScan();
  if (!s) return null;
  const nothingNew = s.opened === 0 && s.review === 0 && s.quarantined === 0;
  return (
    <div className="toast" role="status">
      <button onClick={dismissSummary} aria-label="Dismiss">×</button>
      <strong>{nothingNew ? "No new updates" : "Scan complete"}</strong>
      <div>
        Checked {s.checked} · opened {s.opened} · skipped {s.skipped} unopened · {s.review} waiting for review · {s.quarantined} quarantined
      </div>
    </div>
  );
}
