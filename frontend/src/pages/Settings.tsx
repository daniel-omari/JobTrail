import { useEffect, useState } from "react";
import { api, type Settings as S } from "../api";
import { useScan } from "../scan-context";
import "./Settings.css";

function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="switch">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-label={label} />
      <span>{checked ? "On" : "Off"}</span>
    </label>
  );
}

export function Settings() {
  const { status, refresh, version } = useScan();
  const [s, setS] = useState<S | null>(null);
  const [labels, setLabels] = useState<string[]>([]);
  const [newLabel, setNewLabel] = useState("");
  const [days, setDays] = useState("90");
  useEffect(() => {
    api.settings().then((x) => { setS(x); setDays(String(x.auto_clean_days ?? 90)); });
    api.labels().then(setLabels);
  }, [version]);
  const save = async (patch: Parameters<typeof api.saveSettings>[0]) => { setS(await api.saveSettings(patch)); refresh(); };
  if (!s) return null;

  const excluded = s.excluded_labels;
  const addLabel = (l: string) => { const t = l.trim(); if (t && !excluded.includes(t)) save({ excluded_labels: [...excluded, t] }); setNewLabel(""); };
  const daysNum = Number(days);
  const daysValid = Number.isInteger(daysNum) && daysNum >= 7 && daysNum <= 3650;

  return (
    <div className="page">
      <div className="page-head"><div><h1>Settings</h1><p className="muted">Everything here is stored only on this computer.</p></div></div>

      <div className="card">
        <h2>Excluded labels</h2>
        <p className="muted">Emails with these labels are skipped before anything else. JobTrail won't even check whether they're job-related. This applies to future scans.</p>
        <div className="chips">
          {excluded.length === 0 && <span className="muted small">No labels excluded.</span>}
          {excluded.map((l) => (
            <span className="chip" key={l}>{l}<button aria-label={`Remove ${l}`} onClick={() => save({ excluded_labels: excluded.filter((x) => x !== l) })}>×</button></span>
          ))}
        </div>
        <div className="row-inline">
          <input value={newLabel} placeholder="Label name, e.g. Personal" onChange={(e) => setNewLabel(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addLabel(newLabel)} />
          <button className="btn" onClick={() => addLabel(newLabel)} disabled={!newLabel.trim()}>Exclude</button>
        </div>
        {labels.filter((l) => !excluded.includes(l)).length > 0 && (
          <p className="small muted">Labels in your inbox:{" "}
            {labels.filter((l) => !excluded.includes(l)).map((l) => (
              <button key={l} className="chip chip-add" onClick={() => addLabel(l)}>+ {l}</button>
            ))}
          </p>
        )}
      </div>

      <div className="card setting">
        <div>
          <h2>Scan on startup</h2>
          <p className="muted">Check for new application emails every time JobTrail starts, so it opens up to date. When off, JobTrail never scans unless you press Scan Now.</p>
        </div>
        <Switch checked={s.scan_on_startup} onChange={(v) => save({ scan_on_startup: v })} label="Scan on startup" />
      </div>

      <div className="card setting">
        <div>
          <h2>Auto-clean the Rejected / No Response list</h2>
          <p className="muted">On startup, remove archived entries older than this many days. It never touches the last 7 days, so your weekly export is safe.</p>
          {s.auto_clean_days !== null && (
            <div className="row-inline">
              <input type="number" min={7} max={3650} value={days} onChange={(e) => setDays(e.target.value)} aria-label="Days" />
              <span className="muted small">days</span>
              <button className="btn" disabled={!daysValid || daysNum === s.auto_clean_days} onClick={() => save({ auto_clean_days: daysNum })}>Save</button>
              {!daysValid && <span className="small" style={{ color: "var(--rejected)" }}>Between 7 and 3650.</span>}
            </div>
          )}
        </div>
        <Switch checked={s.auto_clean_days !== null} label="Auto-clean"
          onChange={(v) => save(v ? { auto_clean_days: daysValid ? daysNum : 90 } : { auto_clean_never: true })} />
      </div>

      <div className="card">
        <h2>Local AI</h2>
        <p className="muted" style={{ margin: 0 }}>
          {status?.ai_available
            ? <>Running <strong>{status.model}</strong> on this computer through Ollama. Email text never leaves your machine.</>
            : <>Not available, so JobTrail is using its rules only. Start Ollama with <code>{status?.model}</code> to use the local model.</>}
        </p>
      </div>

      <div className="card setting demo-setting">
        <div>
          <h2>Demo: defences</h2>
          <p className="muted">For demonstrations only. When off, emails go straight to the AI without the injection detector or cross-check, showing what an undefended app would do. Keep this on.</p>
        </div>
        <Switch checked={s.defences} onChange={(v) => save({ defences: v })} label="Defences" />
      </div>
    </div>
  );
}
