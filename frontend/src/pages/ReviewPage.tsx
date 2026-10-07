import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Alert, EmptyState } from "../components/State";
import { Badge } from "../components/Badge";
import { Button } from "../components/Button";
import { useToast } from "../components/Toast";
import { errorMessage, getReview, getReviews, regenerateEmail, rejectDraft, sendDraft } from "../services/api";
import type { EmailDetail, ReviewItem } from "../types";
import { categoryClass, formatWhen, percent, riskClass, riskLabel, urgencyClass } from "../utils/format";

export function ReviewPage() {
  const params = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [queue, setQueue] = useState<ReviewItem[]>([]);
  const [current, setCurrent] = useState<EmailDetail | null>(null);
  const [draftText, setDraftText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  const requestedId = params.draftId ? Number(params.draftId) : null;

  async function refreshQueue() {
    const items = await getReviews();
    setQueue(items);
    return items;
  }

  useEffect(() => {
    let active = true;
    refreshQueue()
      .then((items) => {
        if (!active) return;
        if (!requestedId && items[0]) navigate(`/review/${items[0].draft.id}`, { replace: true });
      })
      .catch((reason) => {
        if (active) setError(errorMessage(reason));
      });
    return () => {
      active = false;
    };
  }, [requestedId, navigate]);

  useEffect(() => {
    if (!requestedId) {
      setCurrent(null);
      return;
    }
    let active = true;
    getReview(requestedId)
      .then((detail) => {
        if (!active) return;
        setCurrent(detail);
        setDraftText(detail.draft?.current_draft ?? "");
        setError("");
      })
      .catch((reason) => {
        if (active) setError(errorMessage(reason));
      });
    return () => {
      active = false;
    };
  }, [requestedId]);

  const edited = useMemo(() => {
    if (!current?.draft) return false;
    return draftText.trim() !== current.draft.original_ai_draft.trim();
  }, [current, draftText]);

  function nextDraft(excludeId: number) {
    const remaining = queue.filter((item) => item.draft.id !== excludeId);
    if (remaining[0]) navigate(`/review/${remaining[0].draft.id}`);
    else navigate("/review");
  }

  async function onSend() {
    if (!current?.draft) return;
    setBusy("send");
    try {
      await sendDraft(current.draft.id, draftText);
      toast(edited ? "Edited reply marked as sent." : "Reply sent.");
      const items = await refreshQueue();
      const remaining = items.filter((item) => item.draft.id !== current.draft?.id);
      if (remaining[0]) navigate(`/review/${remaining[0].draft.id}`);
      else {
        setCurrent(null);
        navigate("/review");
      }
    } catch (reason) {
      toast(errorMessage(reason), "err");
    } finally {
      setBusy("");
    }
  }

  async function onReject() {
    if (!current?.draft) return;
    setBusy("reject");
    try {
      await rejectDraft(current.draft.id, draftText);
      toast("Reply rejected. Nothing was sent.");
      const id = current.draft.id;
      await refreshQueue();
      nextDraft(id);
    } catch (reason) {
      toast(errorMessage(reason), "err");
    } finally {
      setBusy("");
    }
  }

  async function onRegenerate() {
    if (!current) return;
    setBusy("regen");
    try {
      const next = await regenerateEmail(current.id);
      setCurrent(next);
      setDraftText(next.draft?.current_draft ?? "");
      if (next.draft) navigate(`/review/${next.draft.id}`);
      await refreshQueue();
      toast("A new draft is ready.");
    } catch (reason) {
      toast(errorMessage(reason), "err");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Review queue</h1>
        <p className="mt-2 text-sm text-stone-600">Read the email, adjust the reply, then send or reject it.</p>
      </header>
      {error && <Alert>{error}</Alert>}
      {queue.length === 0 && !current && (
        <EmptyState title="You're caught up" body="Nothing is waiting for review. New mail that Sable is unsure about will land here." />
      )}
      {(queue.length > 0 || current) && (
        <div className="grid gap-4 xl:grid-cols-[240px_minmax(0,1fr)_340px]">
          <aside className="rounded-2xl border border-line bg-white shadow-card">
            <p className="border-b border-line px-4 py-3 text-xs font-medium uppercase tracking-wide text-stone-500">{queue.length} waiting</p>
            <div className="max-h-[70vh] divide-y divide-line overflow-auto">
              {queue.map((item) => (
                <Link
                  key={item.draft.id}
                  to={`/review/${item.draft.id}`}
                  className={`block px-4 py-3 ${item.draft.id === requestedId ? "bg-accent-soft" : "hover:bg-stone-50"}`}
                >
                  <p className="truncate text-sm font-medium">{item.email.sender_name}</p>
                  <p className="truncate text-sm text-stone-600">{item.email.subject}</p>
                </Link>
              ))}
            </div>
          </aside>

          <article className="rounded-2xl border border-line bg-white p-5 shadow-card">
            {current ? (
              <>
                <div className="flex flex-wrap gap-1.5">
                  {current.category && <Badge className={categoryClass[current.category]}>{current.category}</Badge>}
                  {current.urgency && <Badge className={urgencyClass[current.urgency]}>{current.urgency}</Badge>}
                  {current.risk_level && <Badge className={riskClass[current.risk_level]}>{riskLabel(current.risk_level)} risk</Badge>}
                </div>
                <p className="mt-4 text-sm text-stone-500">
                  From {current.sender_name} · {formatWhen(current.received_at)}
                </p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight">{current.subject}</h2>
                <div className="mt-5 whitespace-pre-wrap text-sm leading-7 text-stone-800">{current.clean_body}</div>
                {current.ai?.analysis?.intent && (
                  <p className="mt-5 rounded-xl bg-paper px-3 py-3 text-sm text-stone-700">
                    <span className="font-medium">Intent. </span>
                    {current.ai.analysis.intent}
                    {current.ai.analysis.required_action ? ` ${current.ai.analysis.required_action}.` : ""}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-stone-500">Choose a message from the queue.</p>
            )}
          </article>

          <aside className="rounded-2xl border border-line bg-white p-5 shadow-card">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-semibold">AI suggested reply</h2>
            </div>
            <p className="mt-1 text-sm text-stone-500">
              Confidence {percent(current?.ai?.confidence_score)} · Risk {riskLabel(current?.ai?.risk_level)}
            </p>
            {(current?.ai?.issues ?? []).length > 0 && (
              <ul className="mt-3 space-y-1 text-xs text-stone-600">
                {current?.ai?.issues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            )}
            <label className="mt-4 block text-sm font-medium" htmlFor="reply">
              Reply
            </label>
            <textarea
              id="reply"
              value={draftText}
              onChange={(event) => setDraftText(event.target.value)}
              className="mt-2 min-h-72 w-full resize-y rounded-xl border border-line bg-paper px-3 py-3 text-sm leading-6 outline-none focus:border-accent"
            />
            <div className="mt-4 grid gap-2">
              <Button onClick={onSend} loading={busy === "send"} disabled={!draftText.trim()}>
                {edited ? "Edit & Send" : "Approve & Send"}
              </Button>
              <Button variant="secondary" onClick={onRegenerate} loading={busy === "regen"} disabled={!current}>
                Regenerate
              </Button>
              <Button variant="danger" onClick={onReject} loading={busy === "reject"} disabled={!current}>
                Reject
              </Button>
            </div>
            <p className="mt-3 text-xs leading-5 text-stone-500">
              In demo mode, sending only updates this inbox. If you change the wording, both the original draft and your version are saved.
            </p>
          </aside>
        </div>
      )}
    </div>
  );
}
