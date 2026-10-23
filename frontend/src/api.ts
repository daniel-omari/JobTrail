// Typed calls to the local backend. Same origin only: the CSP blocks anything else.

export type Status = "Applied" | "Assessment" | "Interview" | "Offer" | "Rejected" | "Closed";

export interface ScanSummary {
  checked: number; opened: number; skipped: number; already_seen: number;
  review: number; quarantined: number; tracked: number;
  mode: string; defences: boolean; skipped_by_reason: Record<string, number>;
}

export interface Application {
  id: number; company: string; role: string; source: string; how_applied: string;
  current_status: Status; archived: boolean; manual: boolean;
  applied_date: string | null; last_update: string | null;
  history: { status: Status; event_date: string }[];
}

export interface LedgerEntry {
  id: number; opened_at: string; sender: string | null; subject: string | null;
  rule: string; stored_summary: string | null; redacted: boolean;
}

export interface LedgerResponse {
  entries: LedgerEntry[];
  skipped_unopened_total: number;
  last_scan: (Omit<ScanSummary, "skipped_by_reason" | "already_seen" | "tracked"> & { ran_at: string }) | null;
}

export interface AppStatus {
  ai_available: boolean; mode: string; model: string | null; defences: boolean;
  review_count: number; quarantine_count: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  scan: () => request<ScanSummary>("/api/scan", { method: "POST" }),
  status: () => request<AppStatus>("/api/status"),
  applications: (archived = false) => request<Application[]>(`/api/applications?archived=${archived}`),
  ledger: () => request<LedgerResponse>("/api/ledger"),
};
