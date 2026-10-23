import type { Status } from "../api";

const LABEL: Record<Status, string> = {
  Applied: "Still pending reply…",
  Assessment: "Stage: Assessment",
  Interview: "Stage: Interview!",
  Offer: "Stage: Offer!",
  Rejected: "Rejected",
  Closed: "Closed",
};

export function stageClass(s: Status): string {
  if (s === "Applied") return "badge-sent";
  if (s === "Assessment" || s === "Interview" || s === "Offer") return "badge-proceeding";
  if (s === "Rejected") return "badge-rejected";
  return "badge-neutral";
}

export function StageBadge({ status }: { status: Status }) {
  return <span className={`badge ${stageClass(status)}`}>{LABEL[status]}</span>;
}
