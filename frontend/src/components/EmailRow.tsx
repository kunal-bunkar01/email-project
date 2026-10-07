import { Link } from "react-router-dom";
import { Badge } from "./Badge";
import type { EmailSummary } from "../types";
import { avatarTone, categoryClass, initials, relativeTime, riskClass, riskLabel, statusClass, statusLabel, urgencyClass } from "../utils/format";

export function EmailBadges({ email }: { email: EmailSummary }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {email.category && <Badge className={categoryClass[email.category] ?? categoryClass.Other}>{email.category}</Badge>}
      {email.urgency && <Badge className={urgencyClass[email.urgency] ?? urgencyClass.Low}>{email.urgency}</Badge>}
      <Badge className={statusClass[email.status] ?? statusClass.unprocessed}>{statusLabel[email.status] ?? email.status}</Badge>
      {email.risk_level && <Badge className={riskClass[email.risk_level] ?? riskClass.LOW}>{riskLabel(email.risk_level)} risk</Badge>}
    </div>
  );
}

export function EmailRow({
  email,
  selected,
  onSelect,
}: {
  email: EmailSummary;
  selected?: boolean;
  onSelect?: () => void;
}) {
  const content = (
    <div className={`flex gap-3 px-4 py-3 ${selected ? "bg-accent-soft/60" : "hover:bg-stone-50"}`}>
      <div className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${avatarTone(email.sender_email)}`}>
        {initials(email.sender_name || email.sender_email)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <p className="truncate text-sm font-semibold text-ink">{email.sender_name || email.sender_email}</p>
          <p className="shrink-0 text-xs text-stone-500">{relativeTime(email.received_at)}</p>
        </div>
        <p className="truncate text-sm text-ink">{email.subject}</p>
        <p className="truncate text-sm text-stone-500">{email.snippet}</p>
        <div className="mt-2">
          <EmailBadges email={email} />
        </div>
      </div>
    </div>
  );

  if (onSelect) {
    return (
      <button type="button" onClick={onSelect} className="block w-full text-left">
        {content}
      </button>
    );
  }
  return (
    <Link to={`/emails/${email.id}`} className="block">
      {content}
    </Link>
  );
}
