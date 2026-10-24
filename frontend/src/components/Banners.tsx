import { useScan } from "../scan-context";

/** Status strips under the nav: connection/request errors, defences off (demo), and rules-only mode. */
export function Banners() {
  const { status, error, clearError, refresh } = useScan();
  return (
    <>
      {error && (
        <div className="banner banner-error" role="alert">
          <div className="banner-inner banner-row">
            <strong>{error}</strong>
            <span>
              <button className="btn" onClick={() => { clearError(); refresh(); }}>Try again</button>{" "}
              <button className="btn" onClick={clearError}>Dismiss</button>
            </span>
          </div>
        </div>
      )}
      {status && !status.defences && (
        <div className="banner banner-warning" role="alert">
          <div className="banner-inner">
            <strong>Defences are OFF (demo mode).</strong> Emails go straight to the AI with no injection checks. Turn them back on in Settings.
          </div>
        </div>
      )}
      {status && !status.ai_available && (
        <div className="banner banner-info" role="status">
          <div className="banner-inner">
            <strong>Local AI unavailable — running in rules-only mode.</strong> Scans still work; start Ollama to use the local model ({status.model}).
          </div>
        </div>
      )}
    </>
  );
}
