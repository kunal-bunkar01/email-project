import { NavLink } from "react-router-dom";
import { Activity, Inbox, LayoutDashboard, Send, Settings, ShieldCheck, X } from "lucide-react";
import { cn } from "../utils/format";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/emails", label: "Inbox", icon: Inbox, end: false },
  { to: "/review", label: "Review queue", icon: ShieldCheck, end: false },
  { to: "/sent", label: "Sent", icon: Send, end: false },
  { to: "/activity", label: "Activity", icon: Activity, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
];

export function Sidebar({
  open,
  reviewCount,
  demo,
  onClose,
}: {
  open: boolean;
  reviewCount: number;
  demo: boolean;
  onClose: () => void;
}) {
  return (
    <>
      {open && <button className="fixed inset-0 z-30 bg-stone-900/30 md:hidden" onClick={onClose} aria-label="Close menu" />}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-white transition-transform md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-sm font-semibold text-white">S</div>
            <div>
              <p className="text-sm font-semibold tracking-tight">Sable</p>
              <p className="text-xs text-stone-500">Email assistant</p>
            </div>
          </div>
          <button className="rounded-lg p-1 text-stone-500 md:hidden" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        {demo && (
          <div className="mx-4 mb-3 rounded-xl bg-amber-50 px-3 py-2 text-xs font-medium text-amber-950">Demo inbox</div>
        )}
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    "flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium text-stone-600 hover:bg-stone-50",
                    isActive && "bg-accent-soft text-accent-dark",
                  )
                }
              >
                <span className="flex items-center gap-3">
                  <Icon size={18} />
                  {link.label}
                </span>
                {link.to === "/review" && reviewCount > 0 && (
                  <span className="rounded-full bg-accent px-2 py-0.5 text-xs text-white">{reviewCount}</span>
                )}
              </NavLink>
            );
          })}
        </nav>
        <p className="px-5 py-4 text-xs leading-5 text-stone-400">Local only. Your mail stays on this machine.</p>
      </aside>
    </>
  );
}
