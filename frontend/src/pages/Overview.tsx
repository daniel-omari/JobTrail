import { useEffect, useState } from "react";
import { api, type LedgerResponse, type OverviewData, type Range } from "../api";
import { SegmentedGauge } from "../components/Gauge";
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

  const segments = [
    { value: data.proceeding_now, color: "var(--proceeding)", label: "Proceeding", hint: "Assessment, interview or offer" },
    { value: data.awaiting_now, color: "var(--sent)", label: "Awaiting reply", hint: "Sent, no outcome yet" },
    { value: data.ended_now, color: "var(--rejected)", label: "Rejected / no response", hint: "Rejected or role closed" },
  ];
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

      <div className="card overview-card">
        {data.active === 0 ? (
          <div className="empty"><h2>No activity {PERIOD[range]}</h2><p>Try This month or All time.</p></div>
        ) : (
          <>
            <SegmentedGauge segments={segments} total={data.active} centreLabel={`applications ${PERIOD[range]}`} />
            <div className="legend">
              {segments.map((s) => (
                <div className="legend-item" key={s.label}>
                  <span className="legend-dot" style={{ background: s.color }} />
                  <div>
                    <div className="legend-count" style={{ color: s.color }}>{s.value}</div>
                    <div className="legend-label">{s.label}</div>
                    <div className="legend-hint">{s.hint}</div>
                  </div>
                </div>
              ))}
            </div>
            <p className="sent-line">
              <strong style={{ color: "var(--sent)" }}>{data.sent}</strong> new application{data.sent === 1 ? "" : "s"} sent {PERIOD[range]}
            </p>
          </>
        )}
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
