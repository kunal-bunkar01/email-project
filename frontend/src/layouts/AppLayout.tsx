import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Menu } from "lucide-react";
import { Sidebar } from "../components/Sidebar";
import { getAuthStatus, getStats } from "../services/api";
import type { AuthStatus } from "../types";

export function AppLayout() {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [reviewCount, setReviewCount] = useState(0);

  useEffect(() => {
    let active = true;
    getAuthStatus()
      .then((next) => {
        if (active) setStatus(next);
      })
      .catch(() => {
        if (active) setStatus(null);
      });
    getStats()
      .then((stats) => {
        if (active) setReviewCount(stats.cards.needs_review);
      })
      .catch(() => {
        if (active) setReviewCount(0);
      });
    return () => {
      active = false;
    };
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-paper">
      <Sidebar open={open} reviewCount={reviewCount} demo={Boolean(status?.demo_mode)} onClose={() => setOpen(false)} />
      <div className="md:pl-64">
        <div className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-paper/90 px-4 py-3 backdrop-blur md:hidden">
          <button className="rounded-lg p-1" onClick={() => setOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <span className="font-semibold">Sable</span>
        </div>
        <main className="mx-auto max-w-7xl px-4 py-6 md:px-8 md:py-8">
          {status?.demo_mode && (
            <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
              <span className="font-semibold">Demo mode.</span> You are looking at a sample inbox with simulated replies. Nothing is sent through Gmail.
            </div>
          )}
          {status && !status.demo_mode && !status.ai_configured && (
            <div className="mb-6 rounded-2xl border border-line bg-white px-4 py-3 text-sm text-stone-700">
              AI provider not configured. Add an OpenAI key in <span className="font-medium">backend/.env</span>, or turn demo mode on to explore the app.
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
