import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type AppStatus, type ScanSummary } from "./api";

interface ScanState {
  version: number;          // bumps after every change so pages refetch
  scanning: boolean;
  lastSummary: ScanSummary | null;
  status: AppStatus | null;
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

  useEffect(() => { api.status().then(setStatus).catch(() => setStatus(null)); }, [version]);

  const refresh = useCallback(() => setVersion((v) => v + 1), []);
  const scan = useCallback(async () => {
    setScanning(true);
    try {
      setLastSummary(await api.scan());
      refresh();
    } finally {
      setScanning(false);
    }
  }, [refresh]);

  return (
    <Ctx.Provider value={{ version, scanning, lastSummary, status, scan, refresh, dismissSummary: () => setLastSummary(null) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useScan(): ScanState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useScan outside ScanProvider");
  return v;
}
