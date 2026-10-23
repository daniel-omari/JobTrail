import { useEffect, useState } from "react";
import { api, type Settings as S } from "../api";
import { useScan } from "../scan-context";
import "./Settings.css";

export function Settings() {
  const { status, refresh, version } = useScan();
  const [s, setS] = useState<S | null>(null);
  useEffect(() => { api.settings().then(setS); }, [version]);
  const save = async (patch: Parameters<typeof api.saveSettings>[0]) => { setS(await api.saveSettings(patch)); refresh(); };
  if (!s) return null;
  return (
    <div className="page">
      <div className="page-head"><div><h1>Settings</h1><p className="muted">Everything here is stored only on this computer.</p></div></div>

      <div className="card">
        <h2>Local AI</h2>
        <p>
          {status?.ai_available
            ? <>Running <strong>{status.model}</strong> on this computer through Ollama. Email text never leaves your machine.</>
            : <>Not available, so JobTrail is using its rules only. Start Ollama with <code>{status?.model}</code> to use the local model.</>}
        </p>
      </div>

      <div className="card setting">
        <div>
          <h2>Demo: defences</h2>
          <p className="muted">For demonstrations only. When off, emails go straight to the AI without the injection detector or cross-check, showing what an undefended app would do. Keep this on.</p>
        </div>
        <label className="switch">
          <input type="checkbox" checked={s.defences} onChange={(e) => save({ defences: e.target.checked })} />
          <span>{s.defences ? "On" : "Off"}</span>
        </label>
      </div>
      <p className="small muted">More settings (excluded labels, scan on startup, auto-clean) arrive in a later step.</p>
    </div>
  );
}
