import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { EmailBadges, EmailRow } from "../components/EmailRow";
import { Alert, EmptyState } from "../components/State";
import { errorMessage, listEmails } from "../services/api";
import type { EmailSummary } from "../types";
import { categories, formatWhen, statuses, statusLabel, urgencies } from "../utils/format";

export function EmailsPage({
  title = "Inbox",
  description = "Search, filter, and open any message Sable has seen.",
  lockedStatus = "",
}: {
  title?: string;
  description?: string;
  lockedStatus?: string;
}) {
  const navigate = useNavigate();
  const [items, setItems] = useState<EmailSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [urgency, setUrgency] = useState("");
  const [status, setStatus] = useState(lockedStatus);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const pageSize = 12;

  useEffect(() => {
    setStatus(lockedStatus);
    setPage(1);
  }, [lockedStatus]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listEmails({
      q: query || undefined,
      category: category || undefined,
      urgency: urgency || undefined,
      status: status || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      page,
      page_size: pageSize,
    })
      .then((result) => {
        if (!active) return;
        setItems(result.items);
        setTotal(result.total);
        setSelected((current) => current ?? result.items[0]?.id ?? null);
        setError("");
      })
      .catch((reason) => {
        if (active) setError(errorMessage(reason));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [query, category, urgency, status, dateFrom, dateTo, page]);

  const selectedEmail = items.find((item) => item.id === selected) ?? items[0];
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-stone-600">{description}</p>
      </header>
      {error && <Alert>{error}</Alert>}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <section className="overflow-hidden rounded-2xl border border-line bg-white shadow-card">
          <div className="space-y-3 border-b border-line p-4">
            <label className="flex items-center gap-2 rounded-xl border border-line bg-paper px-3 py-2">
              <Search size={16} className="text-stone-400" />
              <input
                value={query}
                onChange={(event) => {
                  setPage(1);
                  setQuery(event.target.value);
                }}
                placeholder="Search sender, subject, or message"
                className="w-full bg-transparent text-sm outline-none"
              />
            </label>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              <Select label="Category" value={category} onChange={(value) => { setPage(1); setCategory(value); }} options={categories} />
              <Select label="Urgency" value={urgency} onChange={(value) => { setPage(1); setUrgency(value); }} options={urgencies} />
              {!lockedStatus && (
                <Select
                  label="Status"
                  value={status}
                  onChange={(value) => { setPage(1); setStatus(value); }}
                  options={statuses}
                  labels={statusLabel}
                />
              )}
              <label className="text-xs font-medium text-stone-500">
                From
                <input type="date" value={dateFrom} onChange={(event) => { setPage(1); setDateFrom(event.target.value); }} className="mt-1 w-full rounded-xl border border-line bg-white px-2 py-2 text-sm text-ink" />
              </label>
              <label className="text-xs font-medium text-stone-500">
                To
                <input type="date" value={dateTo} onChange={(event) => { setPage(1); setDateTo(event.target.value); }} className="mt-1 w-full rounded-xl border border-line bg-white px-2 py-2 text-sm text-ink" />
              </label>
            </div>
          </div>
          {loading && <p className="px-4 py-8 text-sm text-stone-500">Loading mail…</p>}
          {!loading && items.length === 0 && (
            <div className="p-4">
              <EmptyState title="No messages match" body="Try a different search or clear the filters." />
            </div>
          )}
          <div className="divide-y divide-line">
            {items.map((email) => (
              <EmailRow key={email.id} email={email} selected={email.id === selectedEmail?.id} onSelect={() => setSelected(email.id)} />
            ))}
          </div>
          <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
            <span className="text-stone-500">{total} messages</span>
            <div className="flex items-center gap-2">
              <button className="rounded-lg px-2 py-1 disabled:opacity-40" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                Previous
              </button>
              <span>
                {page} / {pages}
              </span>
              <button className="rounded-lg px-2 py-1 disabled:opacity-40" disabled={page >= pages} onClick={() => setPage((current) => current + 1)}>
                Next
              </button>
            </div>
          </div>
        </section>
        <aside className="hidden xl:block">
          {selectedEmail ? (
            <div className="sticky top-6 rounded-2xl border border-line bg-white p-5 shadow-card">
              <EmailBadges email={selectedEmail} />
              <p className="mt-4 text-xs uppercase tracking-wide text-stone-500">{selectedEmail.sender_email}</p>
              <h2 className="mt-1 text-xl font-semibold tracking-tight">{selectedEmail.subject}</h2>
              <p className="mt-1 text-sm text-stone-500">{formatWhen(selectedEmail.received_at)}</p>
              <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-stone-700">{selectedEmail.snippet}</p>
              <div className="mt-5 flex gap-3">
                <button className="rounded-xl bg-accent px-3 py-2 text-sm font-medium text-white" onClick={() => navigate(`/emails/${selectedEmail.id}`)}>
                  Open
                </button>
                {selectedEmail.draft_id && (
                  <Link to={`/review/${selectedEmail.draft_id}`} className="rounded-xl border border-line px-3 py-2 text-sm font-medium">
                    Review reply
                  </Link>
                )}
              </div>
            </div>
          ) : (
            <EmptyState title="Select a message" body="The preview appears here." />
          )}
        </aside>
      </div>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
  labels,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  labels?: Record<string, string>;
}) {
  return (
    <label className="text-xs font-medium text-stone-500">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="mt-1 w-full rounded-xl border border-line bg-white px-2 py-2 text-sm text-ink">
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {labels?.[option] ?? option}
          </option>
        ))}
      </select>
    </label>
  );
}
