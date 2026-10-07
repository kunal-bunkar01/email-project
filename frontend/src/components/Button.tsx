import { cn } from "../utils/format";

type Variant = "primary" | "secondary" | "danger" | "ghost";

export function Button({
  children,
  variant = "primary",
  type = "button",
  className,
  loading,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  const styles: Record<Variant, string> = {
    primary: "bg-accent text-white hover:bg-accent-dark",
    secondary: "border border-line bg-white text-ink hover:bg-stone-50",
    danger: "border border-rose-200 bg-white text-rose-800 hover:bg-rose-50",
    ghost: "text-stone-600 hover:bg-stone-100",
  };
  return (
    <button
      {...props}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        styles[variant],
        className,
      )}
      disabled={props.disabled || loading}
    >
      {loading ? "Working…" : children}
    </button>
  );
}
