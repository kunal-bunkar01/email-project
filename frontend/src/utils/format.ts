export function cn(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function formatWhen(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function formatDay(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date);
}

export function relativeTime(value: string | null | undefined) {
  if (!value) return "";
  const date = new Date(value);
  const delta = Date.now() - date.getTime();
  const minutes = Math.round(delta / 60000);
  if (Math.abs(minutes) < 1) return "Just now";
  if (Math.abs(minutes) < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 7) return `${days}d ago`;
  return formatWhen(value);
}

export function percent(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

export function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = (parts[0]?.[0] ?? "?").toUpperCase() + (parts[1]?.[0] ?? "").toUpperCase();
  return letters;
}

const avatarTones = [
  "bg-emerald-100 text-emerald-900",
  "bg-amber-100 text-amber-900",
  "bg-stone-200 text-stone-800",
  "bg-teal-100 text-teal-900",
  "bg-orange-100 text-orange-900",
  "bg-lime-100 text-lime-900",
];

export function avatarTone(seed: string) {
  let total = 0;
  for (const char of seed) total += char.charCodeAt(0);
  return avatarTones[total % avatarTones.length];
}

export const categoryClass: Record<string, string> = {
  Work: "bg-emerald-50 text-emerald-900 ring-emerald-200",
  Personal: "bg-orange-50 text-orange-900 ring-orange-200",
  Finance: "bg-amber-50 text-amber-950 ring-amber-200",
  Support: "bg-teal-50 text-teal-900 ring-teal-200",
  Promotion: "bg-fuchsia-50 text-fuchsia-900 ring-fuchsia-200",
  Newsletter: "bg-stone-100 text-stone-700 ring-stone-200",
  Spam: "bg-rose-50 text-rose-800 ring-rose-200",
  Other: "bg-stone-100 text-stone-700 ring-stone-200",
};

export const urgencyClass: Record<string, string> = {
  High: "bg-rose-50 text-rose-800 ring-rose-200",
  Medium: "bg-amber-50 text-amber-900 ring-amber-200",
  Low: "bg-stone-100 text-stone-700 ring-stone-200",
};

export const riskClass: Record<string, string> = {
  LOW: "bg-emerald-50 text-emerald-900 ring-emerald-200",
  MEDIUM: "bg-amber-50 text-amber-900 ring-amber-200",
  HIGH: "bg-rose-50 text-rose-800 ring-rose-200",
};

export const statusLabel: Record<string, string> = {
  unprocessed: "Not processed",
  processing: "Processing",
  pending_review: "Needs review",
  auto_sent: "Auto sent",
  sent: "Sent",
  rejected: "Rejected",
  processed: "No reply",
  failed: "Failed",
  pending: "Needs review",
  no_reply: "No reply",
};

export const statusClass: Record<string, string> = {
  unprocessed: "bg-stone-100 text-stone-700 ring-stone-200",
  processing: "bg-amber-50 text-amber-900 ring-amber-200",
  pending_review: "bg-amber-50 text-amber-950 ring-amber-200",
  pending: "bg-amber-50 text-amber-950 ring-amber-200",
  auto_sent: "bg-emerald-50 text-emerald-900 ring-emerald-200",
  sent: "bg-emerald-50 text-emerald-900 ring-emerald-200",
  rejected: "bg-stone-100 text-stone-600 ring-stone-200",
  processed: "bg-stone-100 text-stone-700 ring-stone-200",
  failed: "bg-rose-50 text-rose-800 ring-rose-200",
};

export function riskLabel(level: string | null | undefined) {
  if (!level) return "Not scored";
  if (level === "LOW") return "Low";
  if (level === "MEDIUM") return "Medium";
  if (level === "HIGH") return "High";
  return level;
}

export function routingLabel(value: string | null | undefined) {
  if (value === "AUTO_SEND") return "Auto send";
  if (value === "PENDING_REVIEW") return "Human review";
  if (value === "NO_REPLY") return "No reply";
  if (value === "FAILED") return "Failed";
  return value || "Not routed";
}

export const categories = ["Work", "Personal", "Finance", "Support", "Promotion", "Newsletter", "Spam", "Other"];
export const urgencies = ["High", "Medium", "Low"];
export const statuses = [
  "unprocessed",
  "pending_review",
  "auto_sent",
  "sent",
  "rejected",
  "processed",
  "failed",
];

export function fileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
