import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert } from "../components/State";
import { Badge } from "../components/Badge";
import { Button } from "../components/Button";
import { useToast } from "../components/Toast";
import { errorMessage, getEmail, processEmail, regenerateEmail } from "../services/api";
import type { EmailDetail } from "../types";
import {
  categoryClass,
  fileSize,
  formatWhen,
  percent,
  riskClass,
  riskLabel,
  routingLabel,
  statusClass,
  statusLabel,
  urgencyClass,
} from "../utils/format";

export function EmailDetailPage() {
  const params = useParams();
  const toast = useToast();
  const emailId = Number(params.id);
  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function load() {
    return getEmail(emailId)
      .then(setEmail)
      .catch((reason) => setError(errorMessage(reason)));
  }

  useEffect(() => {
    if (!Number.isFinite(emailId)) return;
    load();
  }, [emailId]);

  async function run(action: "process" | "regenerate") {
    setBusy(true);
    try {
      const next = action === "process" ? await processEmail(emailId) : await regenerateEmail(emailId);
      setEmail(next);
      toast(action === "process" ? "Email processed." : "A new reply is ready.");
    } catch (reason) {
      toast(errorMessage(reason), "err");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <Alert>{error}</Alert>;
  if (!email) return <p className="text-sm text-stone-500">Loading email…</p>;
  const analysis = email.ai?.analysis;

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
        <div>
          <Link to="/emails" className="text-sm font-medium text-accent">
            Back to inbox
          </Link>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{email.subject}</h1>
          <p className="mt-2 text-sm text-stone-600">
            {email.sender_name} · {email.sender_email} · {formatWhen(email.received_at)}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {email.category && <Badge className={categoryClass[email.category]}>{email.category}</Badge>}
            {email.urgency && <Badge className={urgencyClass[email.urgency]}>{email.urgency}</Badge>}
            <Badge className={statusClass[email.status]}>{statusLabel[email.status] ?? email.status}</Badge>
            {email.risk_level && <Badge className={riskClass[email.risk_level]}>{riskLabel(email.risk_level)} risk</Badge>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {(email.status === "unprocessed" || email.status === "failed") && (
            <Button loading={busy} onClick={() => run("process")}>
              Process
            </Button>
          )}
          {email.is_processed && (
            <Button variant="secondary" loading={busy} onClick={() => run("regenerate")}>
              Regenerate
            </Button>
          )}
          {email.draft?.status === "pending" && (
            <Link to={`/review/${email.draft.id}`} className="inline-flex items-center rounded-xl bg-accent px-3.5 py-2 text-sm font-medium text-white">
              Review reply
            </Link>
          )}
        </div>
      </div>

      {email.error_message && <Alert>{email.error_message}</Alert>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
        <article className="rounded-2xl border border-line bg-white p-6 shadow-card">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">From {email.sender_name}</p>
          <h2 className="mt-2 text-lg font-semibold">{email.subject}</h2>
          <div className="mt-5 whitespace-pre-wrap text-sm leading-7 text-stone-800">{email.clean_body || email.body}</div>
          {email.attachments.length > 0 && (
            <div className="mt-6 border-t border-line pt-4">
              <h3 className="text-sm font-semibold">Attachments</h3>
              <ul className="mt-3 space-y-3">
                {email.attachments.map((file) => (
                  <li key={file.id} className="rounded-xl bg-paper px-3 py-3 text-sm">
                    <p className="font-medium">
                      {file.filename} <span className="font-normal text-stone-500">· {file.mime_type} · {fileSize(file.size)}</span>
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-stone-600">{file.extracted_text || "No text extracted."}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </article>

        <aside className="space-y-4">
          <InfoCard title="Classification" body={email.ai?.classification.reason} extra={email.category ? `${email.category} · ${percent(email.ai?.classification.confidence)}` : "Not classified"} />
          <InfoCard title="Urgency" body={email.ai?.urgency.reason} extra={email.urgency ? `${email.urgency} · ${percent(email.ai?.urgency.confidence)}` : "Not scored"} />
          <section className="rounded-2xl border border-line bg-white p-4 shadow-card">
            <h2 className="font-semibold">What the email is asking</h2>
            {analysis ? (
              <dl className="mt-3 space-y-3 text-sm">
                <Row label="Intent" value={analysis.intent} />
                <Row label="Needed action" value={analysis.required_action} />
                <Row label="Deadline" value={analysis.deadline || "None found"} />
                <Row label="Sentiment" value={analysis.sentiment} />
                <Row label="Strategy" value={analysis.response_strategy} />
              </dl>
            ) : (
              <p className="mt-2 text-sm text-stone-500">Process this email to see an analysis.</p>
            )}
            {analysis?.key_points && analysis.key_points.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-stone-700">
                {analysis.key_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>

      {email.thread.length > 1 && (
        <section className="rounded-2xl border border-line bg-white p-5 shadow-card">
          <h2 className="font-semibold">Thread</h2>
          <div className="mt-4 space-y-4">
            {email.thread.map((message) => (
              <div key={message.id} className={`rounded-xl px-4 py-3 ${message.is_current ? "bg-accent-soft" : "bg-paper"}`}>
                <p className="text-sm font-medium">
                  {message.sender_name} <span className="font-normal text-stone-500">{formatWhen(message.received_at)}</span>
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-stone-700">{message.clean_body}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {email.draft && (
        <section className="grid gap-4 lg:grid-cols-2">
          <article className="rounded-2xl border border-line bg-white p-5 shadow-card">
            <h2 className="font-semibold">Suggested reply</h2>
            <p className="mt-1 text-sm text-stone-500">
              Confidence {percent(email.ai?.confidence_score)} · Risk {riskLabel(email.ai?.risk_level)} · {routingLabel(email.ai?.routing_decision)}
            </p>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-7">{email.draft.current_draft}</p>
          </article>
          <article className="rounded-2xl border border-line bg-white p-5 shadow-card">
            <h2 className="font-semibold">Risk check</h2>
            <p className="mt-3 text-sm text-stone-600">Score {percent(email.ai?.risk_score)}. Recommendation {routingLabel(email.ai?.recommendation)}.</p>
            <ul className="mt-3 space-y-2 text-sm">
              {(email.ai?.issues ?? []).length === 0 && <li className="text-stone-500">No issues were flagged.</li>}
              {email.ai?.issues.map((issue) => (
                <li key={issue} className="rounded-xl bg-paper px-3 py-2">
                  {issue}
                </li>
              ))}
            </ul>
          </article>
        </section>
      )}

      <section className="rounded-2xl border border-line bg-white p-5 shadow-card">
        <h2 className="font-semibold">Processing history</h2>
        <ul className="mt-4 space-y-3">
          {email.activity.map((item) => (
            <li key={item.id} className="flex gap-3 text-sm">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent" />
              <span>
                {item.message}
                <span className="ml-2 text-stone-500">{formatWhen(item.created_at)}</span>
              </span>
            </li>
          ))}
          {email.activity.length === 0 && <li className="text-sm text-stone-500">No processing history yet.</li>}
        </ul>
        {email.feedback.length > 0 && (
          <div className="mt-5 border-t border-line pt-4">
            <h3 className="text-sm font-semibold">Human review</h3>
            {email.feedback.map((item) => (
              <div key={item.id} className="mt-3 text-sm text-stone-700">
                <p className="font-medium capitalize">{item.feedback_type}</p>
                {item.human_final_reply && <p className="mt-1 whitespace-pre-wrap">{item.human_final_reply}</p>}
              </div>
            ))}
          </div>
        )}
        <details className="mt-5 text-sm">
          <summary className="cursor-pointer font-medium text-stone-600">Technical details</summary>
          <pre className="mt-3 overflow-auto rounded-xl bg-paper p-3 text-xs leading-5 text-stone-700">
            {JSON.stringify(
              {
                labels: email.labels,
                recipients: email.recipients,
                cc: email.cc,
                in_reply_to: email.in_reply_to,
                classification: email.ai?.classification,
                urgency: email.ai?.urgency,
                analysis: email.ai?.analysis,
                routing: email.ai?.routing_decision,
                model: email.ai?.model_name,
                seconds: email.ai?.processing_time,
              },
              null,
              2,
            )}
          </pre>
        </details>
      </section>
    </div>
  );
}

function InfoCard({ title, extra, body }: { title: string; extra: string; body?: string }) {
  return (
    <section className="rounded-2xl border border-line bg-white p-4 shadow-card">
      <p className="text-xs font-medium uppercase tracking-wide text-stone-500">{title}</p>
      <p className="mt-1 font-semibold">{extra}</p>
      {body && <p className="mt-2 text-sm leading-6 text-stone-600">{body}</p>}
    </section>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-stone-500">{label}</dt>
      <dd className="mt-0.5 text-stone-800">{value || "—"}</dd>
    </div>
  );
}
