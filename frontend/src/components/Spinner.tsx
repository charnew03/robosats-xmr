export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-xmr-muted border-t-xmr-accent ${className}`}
      aria-hidden
    />
  );
}
