import { useEffect } from "react";

export type ToastKind = "success" | "error" | "info";

export type ToastState = {
  id: number;
  kind: ToastKind;
  message: string;
} | null;

type Props = {
  toast: ToastState;
  onDismiss: () => void;
};

export function Toast({ toast, onDismiss }: Props) {
  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(onDismiss, toast.kind === "error" ? 7000 : 4500);
    return () => window.clearTimeout(t);
  }, [toast, onDismiss]);

  if (!toast) return null;

  const styles =
    toast.kind === "success"
      ? "border-emerald-800 bg-emerald-950/90 text-emerald-100"
      : toast.kind === "error"
        ? "border-red-900 bg-red-950/90 text-red-100"
        : "border-xmr-border bg-xmr-panel text-xmr-text";

  return (
    <div
      className={`fixed bottom-4 left-4 right-4 z-[60] mx-auto max-w-md rounded-lg border px-4 py-3 text-sm shadow-lg sm:left-auto sm:right-4 ${styles}`}
      role="status"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="flex-1 break-words">{toast.message}</p>
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 rounded px-2 py-0.5 text-xmr-muted hover:text-xmr-text"
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
    </div>
  );
}
