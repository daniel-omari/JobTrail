import { useScan } from "../scan-context";

export function Overview() {
  const { scan, scanning } = useScan();
  return (
    <div className="page">
      <div className="page-head"><div><h1>Overview</h1><p className="muted">Your job search at a glance.</p></div></div>
      <div className="card empty">
        <h2>Dashboard coming in step 4</h2>
        <p>For now, run a scan and check the Tracker and Privacy pages.</p>
        <button className="btn btn-primary" onClick={scan} disabled={scanning}>Scan Now</button>
      </div>
    </div>
  );
}
