import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert } from "../components/State";
import { errorMessage, getActivity } from "../services/api";
import type { ActivityItem } from "../types";
import { formatWhen } from "../utils/format";

const labels: Record<string, string> = {
  email_classified: "Classified",
  reply_generated: "Reply",
  email_approved: "Approved",
  email_sent: "Sent",
  email_auto_sent: "Auto sent",
  email_rejected: "Rejected",
  email_failed: "Failed",
  email_synced: "Synced",
};

export function ActivityPage() {
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getActivity()
      .then((page) => setItems(page.items))
      .catch((reason) => setError(errorMessage(reason)));
  }, []);

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Activity</h1>
        <p className="mt-2 text-sm text-stone-600">Classification, drafts, approvals, and sends.</p>
      </header>
      {error && <Alert>{error}</Alert>}
      <ol className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded-2xl border border-line bg-white px-5 py-4 shadow-card">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium uppercase tracking-wide text-accent">{labels[item.activity_type] ?? "Update"}</p>
              <p className="text-xs text-stone-500">{formatWhen(item.created_at)}</p>
            </div>
            <p className="mt-2 text-sm">{item.message}</p>
            {item.email_id && (
              <Link to={`/emails/${item.email_id}`} className="mt-2 inline-block text-sm font-medium text-accent">
                Open email
              </Link>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
