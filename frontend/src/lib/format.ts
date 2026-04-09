/** Short pseudonymous id for table display (privacy-friendly). */
export function shortId(id: string, head = 6, tail = 4): string {
  if (id.length <= head + tail + 1) return id;
  return `${id.slice(0, head)}…${id.slice(-tail)}`;
}

export function formatXmr(n: number, decimals = 4): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Premium as signed percent string for display. */
export function formatPremium(pct: number): string {
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

export function formatFiatCurrency(code: string): string {
  return code.trim().toUpperCase();
}
