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

export type Range = "week" | "month" | "all";

export interface OverviewData {
  range: Range; start: string | null; end: string;
  sent: number; proceeding: number; rejected: number; active: number; total_all_time: number;
}

export interface Flag { code: string; reason: string; excerpt: string; info: string }

export interface QuarantineItem {
  id: number; sender: string; subject: string; received_date: string;
  reasons: Flag[];
  rules_prefill: { company: string | null; role: string | null; status: Status | null };
}

export interface Settings {
  defences: boolean; excluded_labels: string[]; scan_on_startup: boolean;
  auto_clean_days: number | null; model: string | null;
}

export interface Fields { company: string; role: string; status: Status }

export const STATUSES: Status[] = ["Applied", "Assessment", "Interview", "Offer", "Rejected", "Closed"];

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
  overview: (range: Range) => request<OverviewData>(`/api/overview?range=${range}`),
  quarantine: () => request<QuarantineItem[]>("/api/quarantine"),
  release: (id: number, f: Fields) => request<{ application_id: number }>(`/api/quarantine/${id}/release`, { method: "POST", body: JSON.stringify(f) }),
  discard: (id: number) => request<{ ok: boolean }>(`/api/quarantine/${id}/discard`, { method: "POST" }),
  settings: () => request<Settings>("/api/settings"),
  saveSettings: (s: Partial<Settings> & { auto_clean_never?: boolean }) => request<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(s) }),
  deleteAll: () => request<{ ok: boolean }>("/api/delete-all?confirm=true", { method: "POST" }),
};
