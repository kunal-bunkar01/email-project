import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Alert } from "../components/State";
import { Button } from "../components/Button";
import { useToast } from "../components/Toast";
import { backendOrigin, errorMessage, getSettings, logout, saveSettings } from "../services/api";
import type { Settings } from "../types";

const tones = ["Professional", "Friendly", "Concise", "Formal", "Casual", "Custom"];
const risks = ["LOW", "MEDIUM", "HIGH"];

export function SettingsPage() {
  const toast = useToast();
  const [params] = useSearchParams();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const gmail = params.get("gmail");
    const message = params.get("message");
    if (gmail === "connected") toast("Gmail connected.");
    if (gmail === "error") toast(message || "Gmail connection failed.", "err");
  }, [params, toast]);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch((reason) => setError(errorMessage(reason)));
  }, []);

  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    setSettings((current) => (current ? { ...current, [key]: value } : current));
  }

  async function onSave() {
    if (!settings) return;
    setSaving(true);
    try {
      const saved = await saveSettings({
        auto_send_enabled: settings.auto_send_enabled,
        auto_send_max_risk: settings.auto_send_max_risk,
        auto_send_min_confidence: Number(settings.auto_send_min_confidence),
        tone: settings.tone,
        custom_instructions: settings.custom_instructions,
        signature: settings.signature,
        processing_enabled: settings.processing_enabled,
        polling_enabled: settings.polling_enabled,
        poll_interval_seconds: Number(settings.poll_interval_seconds),
        review_high_urgency: settings.review_high_urgency,
      });
      setSettings(saved);
      toast("Settings saved.");
    } catch (reason) {
      toast(errorMessage(reason), "err");
    } finally {
      setSaving(false);
    }
  }

  async function onDisconnect() {
    try {
      await logout();
      const next = await getSettings();
      setSettings(next);
      toast("Gmail disconnected on this machine.");
    } catch (reason) {
      toast(errorMessage(reason), "err");
    }
  }

  if (error) return <Alert>{error}</Alert>;
  if (!settings) return <p className="text-sm text-stone-500">Loading settings…</p>;

  return (
    <div className="space-y-6">
      <header className="flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-2 text-sm text-stone-600">How Sable writes, and when it is allowed to send.</p>
        </div>
        <Button onClick={onSave} loading={saving}>
          Save changes
        </Button>
      </header>

      <Section title="Gmail" text="Connect a mailbox when you are ready to leave demo mode.">
        <p className="text-sm">
          <span className="font-medium">{settings.account_name || "Local user"}</span>
          <span className="text-stone-500"> · {settings.account_email || "No address yet"}</span>
        </p>
        <p className="mt-2 text-sm text-stone-600">
          {settings.demo_mode
            ? "Demo mode is simulating Gmail. Set DEMO_MODE=false after adding OAuth credentials."
            : settings.google_connected
              ? "Connected."
              : settings.google_configured
                ? "Credentials are present. Connect to grant access."
                : "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env."}
        </p>
        <div className="mt-4 flex gap-2">
          <Button
            variant="secondary"
            disabled={settings.demo_mode || !settings.google_configured}
            onClick={() => {
              window.location.href = `${backendOrigin}/api/auth/google`;
            }}
          >
            Connect Gmail
          </Button>
          <Button variant="ghost" disabled={!settings.google_connected} onClick={onDisconnect}>
            Disconnect
          </Button>
        </div>
      </Section>

      <Section title="AI" text="The provider is chosen from the environment, not from this form.">
        <p className="text-sm font-medium capitalize">{settings.ai_provider}</p>
        <p className="mt-2 text-sm text-stone-600">{settings.ai_message}</p>
      </Section>

      <Section title="Automation" text="High-risk and incomplete replies are never sent on their own.">
        <Toggle label="Auto-send enabled" checked={settings.auto_send_enabled} onChange={(value) => update("auto_send_enabled", value)} />
        <Toggle
          label="Hold high-urgency emails for review"
          checked={settings.review_high_urgency}
          onChange={(value) => update("review_high_urgency", value)}
        />
        <label className="mt-4 block text-sm font-medium">
          Minimum confidence ({Math.round(settings.auto_send_min_confidence * 100)}%)
          <input
            type="range"
            min={50}
            max={99}
            value={Math.round(settings.auto_send_min_confidence * 100)}
            onChange={(event) => update("auto_send_min_confidence", Number(event.target.value) / 100)}
            className="mt-2 w-full"
          />
        </label>
        <label className="mt-4 block text-sm font-medium">
          Maximum risk allowed to auto-send
          <select
            value={settings.auto_send_max_risk}
            onChange={(event) => update("auto_send_max_risk", event.target.value)}
            className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2"
          >
            {risks.map((risk) => (
              <option key={risk} value={risk}>
                {risk}
              </option>
            ))}
          </select>
        </label>
      </Section>

      <Section title="Tone" text="Replies follow this voice, plus any instructions you add.">
        <label className="block text-sm font-medium">
          Tone
          <select value={settings.tone} onChange={(event) => update("tone", event.target.value)} className="mt-2 w-full rounded-xl border border-line bg-white px-3 py-2">
            {tones.map((tone) => (
              <option key={tone}>{tone}</option>
            ))}
          </select>
        </label>
        <label className="mt-4 block text-sm font-medium">
          Custom instructions
          <textarea
            value={settings.custom_instructions}
            onChange={(event) => update("custom_instructions", event.target.value)}
            className="mt-2 min-h-28 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm"
          />
        </label>
        <label className="mt-4 block text-sm font-medium">
          Signature
          <textarea
            value={settings.signature}
            onChange={(event) => update("signature", event.target.value)}
            className="mt-2 min-h-24 w-full rounded-xl border border-line bg-paper px-3 py-2 text-sm"
          />
        </label>
      </Section>

      <Section title="Processing" text="Polling only runs while the backend is open, and it stays quiet in demo mode.">
        <Toggle label="Automatic email processing" checked={settings.processing_enabled} onChange={(value) => update("processing_enabled", value)} />
        <Toggle label="Background polling" checked={settings.polling_enabled} onChange={(value) => update("polling_enabled", value)} />
        <label className="mt-4 block text-sm font-medium">
          Polling interval (seconds)
          <input
            type="number"
            min={15}
            max={3600}
            value={settings.poll_interval_seconds}
            onChange={(event) => update("poll_interval_seconds", Number(event.target.value))}
            className="mt-2 w-40 rounded-xl border border-line px-3 py-2"
          />
        </label>
      </Section>
    </div>
  );
}

function Section({ title, text, children }: { title: string; text: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-line bg-white p-5 shadow-card">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-1 text-sm text-stone-600">{text}</p>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="mt-3 flex items-center justify-between gap-4 text-sm">
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-accent" />
    </label>
  );
}
