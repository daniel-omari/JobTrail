import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, apiErrors, type AppStatus, type ScanSummary } from "./api";

interface ScanState {
  version: number;          // bumps after every change so pages refetch
  scanning: boolean;
  lastSummary: ScanSummary | null;
  status: AppStatus | null;
  error: string | null;
  clearError: () => void;
  scan: () => Promise<void>;
  refresh: () => void;
  dismissSummary: () => void;
}

const Ctx = createContext<ScanState | null>(null);

export function ScanProvider({ children }: { children: ReactNode }) {
  const [version, setVersion] = useState(0);
  const [scanning, setScanning] = useState(false);
  const [lastSummary, setLastSummary] = useState<ScanSummary | null>(null);
  const [status, setStatus] = useState<AppStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onError = (e: Event) => setError((e as CustomEvent<string>).detail);
    apiErrors.addEventListener("error", onError);
    return () => apiErrors.removeEventListener("error", onError);
  }, []);
  useEffect(() => { api.status().then((s) => { setStatus(s); setError(null); }).catch(() => setStatus(null)); }, [version]);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const scan = useCallback(async () => {
    setScanning(true);
    try {
      setLastSummary(await api.scan());
      refresh();
    } catch {
      /* the error banner already explains what happened */
    } finally {
      setScanning(false);
    }
  }, [refresh]);

  return (
    <Ctx.Provider value={{ version, scanning, lastSummary, status, error, clearError: () => setError(null), scan, refresh, dismissSummary: () => setLastSummary(null) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useScan(): ScanState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useScan outside ScanProvider");
  return v;
}
