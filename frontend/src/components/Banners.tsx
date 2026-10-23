import { useScan } from "../scan-context";

/** Persistent status strips under the nav: rules-only mode, and (later) defences off. */
export function Banners() {
  const { status } = useScan();
  if (!status) return null;
  return (
    <>
      {!status.ai_available && (
        <div className="banner banner-info" role="status">
          <div className="banner-inner">
            <strong>Local AI unavailable — running in rules-only mode.</strong> Scans still work; start Ollama to use the local model ({status.model}).
          </div>
        </div>
      )}
    </>
  );
}
