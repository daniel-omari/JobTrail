import { useEffect, useState } from "react";
import { api } from "../api";
import { useScan } from "../scan-context";

const iso = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const addDays = (s: string, n: number) => { const d = new Date(s + "T12:00:00"); d.setDate(d.getDate() + n); return iso(d); };

export function Export() {
  const { version } = useScan();
  const [start, setStart] = useState(() => addDays(iso(new Date()), -6)); // default: the last 7 days
  const end = addDays(start, 6);
  const [data, setData] = useState<{ count: number; text: string } | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => { api.exportSummary(start, end).then(setData); setCopied(false); }, [start, end, version]);

  const copy = async () => {
    if (!data) return;
    await navigator.clipboard.writeText(data.text);
    setCopied(true);
  };

  const downloadCsv = async () => {
    const res = await fetch(`/api/export?format=csv&start=${start}&end=${end}`);
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url; a.download = `jobtrail-${start}-to-${end}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Export</h1>
          <p className="muted">A weekly summary of your job-search activity, ready to paste into your Universal Credit journal.</p>
        </div>
      </div>
      <div className="card">
        <div className="export-controls">
          <label className="small muted">Week starting{" "}
            <input type="date" value={start} max={iso(new Date())} onChange={(e) => e.target.value && setStart(e.target.value)} />
          </label>
          <span className="small muted">to {new Date(end + "T12:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })} · {data?.count ?? 0} entr{data?.count === 1 ? "y" : "ies"}</span>
          <span style={{ flex: 1 }} />
          <button className="btn btn-primary" onClick={copy} disabled={!data}>{copied ? "Copied ✓" : "Copy summary"}</button>
          <button className="btn" onClick={downloadCsv}>Download CSV</button>
        </div>
        <textarea className="export-text" readOnly value={data?.text ?? ""} aria-label="Weekly summary" />
        <p className="small muted">Check it before pasting. Entries you added or edited yourself are included. Quarantined emails never are.</p>
      </div>
    </div>
  );
}
