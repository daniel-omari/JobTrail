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
  awaiting_now: number; proceeding_now: number; ended_now: number;
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

export interface Everything {
  applications: Application[]; ledger: LedgerEntry[]; review_queue: ReviewItem[];
  quarantine: { sender: string; subject: string; received_date: string; reasons: { reason: string; excerpt: string }[] }[];
  trusted_senders: string[]; rejected_senders: string[]; do_not_track: { company: string; role: string }[];
  settings: Settings; processed_email_fingerprints: number;
  scan_runs: { ran_at: string; checked: number; opened: number; skipped: number; review: number; quarantined: number; mode: string; defences: number }[];
}

export interface ReviewItem { id: number; sender: string; subject: string; received_date: string }

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
  addApplication: (a: Fields & { date?: string; how_applied?: string }) =>
    request<Application>("/api/applications", { method: "POST", body: JSON.stringify(a) }),
  editApplication: (id: number, a: Partial<Fields> & { how_applied?: string }) =>
    request<Application>(`/api/applications/${id}`, { method: "PATCH", body: JSON.stringify(a) }),
  deleteApplication: (id: number) => request<{ ok: boolean }>(`/api/applications/${id}`, { method: "DELETE" }),
  doNotTrack: (id: number) => request<{ ok: boolean }>(`/api/applications/${id}/do-not-track`, { method: "POST" }),
  restore: (id: number) => request<Application>(`/api/applications/${id}/restore`, { method: "POST" }),
  clearArchive: (olderThan: number) => request<{ removed: number }>(`/api/archive/clear?older_than=${olderThan}`, { method: "POST" }),
  forceClean: () => request<{ removed: number }>("/api/archive/force-clean?confirm=true", { method: "POST" }),
  review: () => request<ReviewItem[]>("/api/review"),
  approve: (id: number) => request<{ outcome: string }>(`/api/review/${id}/approve`, { method: "POST" }),
  reject: (id: number) => request<{ outcome: string }>(`/api/review/${id}/reject`, { method: "POST" }),
  quarantine: () => request<QuarantineItem[]>("/api/quarantine"),
  release: (id: number, f: Fields) => request<{ application_id: number }>(`/api/quarantine/${id}/release`, { method: "POST", body: JSON.stringify(f) }),
  discard: (id: number) => request<{ ok: boolean }>(`/api/quarantine/${id}/discard`, { method: "POST" }),
  settings: () => request<Settings>("/api/settings"),
  saveSettings: (s: Partial<Settings> & { auto_clean_never?: boolean }) => request<Settings>("/api/settings", { method: "PUT", body: JSON.stringify(s) }),
  everything: () => request<Everything>("/api/everything"),
  deleteAll: () => request<{ ok: boolean }>("/api/delete-all?confirm=true", { method: "POST" }),
};
