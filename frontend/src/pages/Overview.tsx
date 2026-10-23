import { useEffect, useState } from "react";
import { api, type LedgerResponse, type OverviewData, type Range } from "../api";
import { Gauge } from "../components/Gauge";
import { useScan } from "../scan-context";
import "./Overview.css";

const RANGES: { key: Range; label: string }[] = [
  { key: "week", label: "This week" },
  { key: "month", label: "This month" },
  { key: "all", label: "All time" },
];

const PERIOD: Record<Range, string> = { week: "this week", month: "this month", all: "in total" };

export function Overview() {
  const { version, scan, scanning } = useScan();
  const [range, setRange] = useState<Range>("week"); // always starts on This week
  const [data, setData] = useState<OverviewData | null>(null);
  const [ledger, setLedger] = useState<LedgerResponse | null>(null);
  useEffect(() => { api.overview(range).then(setData); }, [range, version]);
  useEffect(() => { api.ledger().then(setLedger); }, [version]);

  if (!data) return null;

  if (data.total_all_time === 0) {
    return (
      <div className="page">
        <div className="card empty overview-empty">
          <h2>No applications yet</h2>
          <p>Run your first scan. JobTrail checks email headers and only opens emails from recruiting platforms.</p>
          <button className="btn btn-primary" onClick={scan} disabled={scanning}>{scanning ? "Scanning…" : "Scan Now"}</button>
        </div>
      </div>
    );
  }

  const caption = `of ${data.active} application${data.active === 1 ? "" : "s"} with activity ${PERIOD[range]}`;
  const last = ledger?.last_scan;
  return (
    <div className="page">
      <div className="page-head">
        <div><h1>Overview</h1><p className="muted">Your job search at a glance.</p></div>
        <div className="segmented" role="group" aria-label="Time range">
          {RANGES.map((r) => (
            <button key={r.key} className={range === r.key ? "active" : ""} aria-pressed={range === r.key} onClick={() => setRange(r.key)}>
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div className="gauges">
        <div className="card"><Gauge value={data.sent} of={data.active} color="var(--sent)" label="Applications sent" caption={caption} /></div>
        <div className="card"><Gauge value={data.proceeding} of={data.active} color="var(--proceeding)" label="Proceeding" caption="Assessment, interview or offer" /></div>
        <div className="card"><Gauge value={data.rejected} of={data.active} color="var(--rejected)" label="Rejected / no response" caption="Rejected or role closed" /></div>
      </div>
      {last && (
        <p className="small muted last-scan">
          Last scan {new Date(last.ran_at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}:
          {" "}checked {last.checked} emails, opened {last.opened}, skipped {last.skipped} without reading them.
        </p>
      )}
    </div>
  );
}
