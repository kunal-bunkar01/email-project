import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Button } from "../components/Button";
import { EmailRow } from "../components/EmailRow";
import { Alert, EmptyState } from "../components/State";
import { useToast } from "../components/Toast";
import { errorMessage, getStats, syncEmails } from "../services/api";
import type { DashboardStats } from "../types";
import { formatDay } from "../utils/format";

const palette = ["#0F6E56", "#B54708", "#57534E", "#0F766E", "#9A3412", "#3F6212", "#44403C", "#A16207"];

export function DashboardPage() {
  const toast = useToast();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);

  function load() {
    return getStats()
      .then(setStats)
      .catch((reason) => setError(errorMessage(reason)));
  }

  useEffect(() => {
    load();
  }, []);

  async function onSync() {
    setSyncing(true);
    try {
      const result = await syncEmails();
      toast(result.message);
      await load();
    } catch (reason) {
      toast(errorMessage(reason), "err");
    } finally {
      setSyncing(false);
    }
  }

  const today = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date());

  return (
    <div className="space-y-8">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-sm text-stone-500">{today}</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Inbox overview</h1>
          <p className="mt-2 max-w-xl text-sm leading-6 text-stone-600">What needs you, and what Sable already handled.</p>
        </div>
        <Button onClick={onSync} loading={syncing}>
          <RefreshCw size={16} />
          Sync Gmail
        </Button>
      </header>

      {error && <Alert>{error}</Alert>}

      {stats && (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <Stat label="Total emails" value={stats.cards.total} />
            <Stat label="Processed" value={stats.cards.processed} />
            <Stat label="Needs review" value={stats.cards.needs_review} />
            <Stat label="Auto sent" value={stats.cards.auto_sent} />
            <Stat label="Today" value={stats.cards.today} />
          </section>

          <section className="grid gap-4 lg:grid-cols-3">
            <ChartCard title="Processed over time" className="lg:col-span-2">
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={stats.over_time}>
                  <CartesianGrid stroke="#E7E5E4" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={formatDay} tick={{ fontSize: 12, fill: "#78716C" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#78716C" }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#0F6E56" strokeWidth={2.4} dot={false} name="Processed" />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Auto-send vs review">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={stats.routing} dataKey="value" nameKey="name" innerRadius={58} outerRadius={82} paddingAngle={3}>
                    {stats.routing.map((entry, index) => (
                      <Cell key={entry.name} fill={palette[index % palette.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
              <ul className="mt-2 space-y-1 text-sm text-stone-600">
                {stats.routing.map((item, index) => (
                  <li key={item.name} className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: palette[index % palette.length] }} />
                      {item.name}
                    </span>
                    <span className="font-medium text-ink">{item.value}</span>
                  </li>
                ))}
              </ul>
            </ChartCard>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Emails by category">
              {stats.by_category.length === 0 ? (
                <p className="py-10 text-center text-sm text-stone-500">No classified mail yet.</p>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={stats.by_category}>
                    <CartesianGrid stroke="#E7E5E4" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#78716C" }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#78716C" }} axisLine={false} tickLine={false} width={28} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]} name="Emails">
                      {stats.by_category.map((entry, index) => (
                        <Cell key={entry.name} fill={palette[index % palette.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </ChartCard>
            <ChartCard title="Emails by urgency">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={stats.by_urgency}>
                  <CartesianGrid stroke="#E7E5E4" vertical={false} />
                  <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#78716C" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: "#78716C" }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[6, 6, 0, 0]} name="Emails">
                    {stats.by_urgency.map((entry) => (
                      <Cell key={entry.name} fill={entry.name === "High" ? "#B42318" : entry.name === "Medium" ? "#B54708" : "#A8A29E"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </section>

          <section className="grid gap-4 lg:grid-cols-5">
            <div className="overflow-hidden rounded-2xl border border-line bg-white shadow-card lg:col-span-3">
              <div className="flex items-center justify-between border-b border-line px-5 py-4">
                <h2 className="font-semibold">Recent emails</h2>
                <Link to="/emails" className="text-sm font-medium text-accent">
                  View inbox
                </Link>
              </div>
              {stats.recent_emails.length === 0 ? (
                <div className="p-5">
                  <EmptyState title="No mail yet" body="Connect Gmail and sync, or start in demo mode to see a sample inbox." />
                </div>
              ) : (
                <div className="divide-y divide-line">
                  {stats.recent_emails.map((email) => (
                    <EmailRow key={email.id} email={email} />
                  ))}
                </div>
              )}
            </div>
            <div className="rounded-2xl border border-line bg-white shadow-card lg:col-span-2">
              <div className="flex items-center justify-between border-b border-line px-5 py-4">
                <h2 className="font-semibold">Review queue</h2>
                <Link to="/review" className="text-sm font-medium text-accent">
                  Open
                </Link>
              </div>
              <div className="divide-y divide-line">
                {stats.review_queue.length === 0 && <p className="px-5 py-8 text-sm text-stone-500">Nothing is waiting for you.</p>}
                {stats.review_queue.map((email) => (
                  <Link key={email.id} to={email.draft_id ? `/review/${email.draft_id}` : `/emails/${email.id}`} className="block px-5 py-3 hover:bg-stone-50">
                    <p className="truncate text-sm font-medium">{email.sender_name}</p>
                    <p className="truncate text-sm text-stone-600">{email.subject}</p>
                  </Link>
                ))}
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-line bg-white shadow-card">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <h2 className="font-semibold">Activity</h2>
              <Link to="/activity" className="text-sm font-medium text-accent">
                All activity
              </Link>
            </div>
            <ul className="divide-y divide-line">
              {stats.activity.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-4 px-5 py-3 text-sm">
                  <span>{item.message}</span>
                  <span className="shrink-0 text-stone-500">{formatDay(item.created_at.slice(0, 10))}</span>
                </li>
              ))}
              {stats.activity.length === 0 && <li className="px-5 py-8 text-sm text-stone-500">Activity will show up as mail is processed.</li>}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-2xl border border-line bg-white px-4 py-4 shadow-card">
      <p className="text-xs font-medium uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}

function ChartCard({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-line bg-white p-5 shadow-card ${className}`}>
      <h2 className="mb-4 font-semibold">{title}</h2>
      {children}
    </section>
  );
}
