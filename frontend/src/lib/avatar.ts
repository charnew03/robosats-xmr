/** Deterministic hue from pseudonym for privacy-style avatars (no external images). */
export function pseudonymHue(label: string): number {
  let h = 0;
  for (let i = 0; i < label.length; i += 1) {
    h = (h * 31 + label.charCodeAt(i)) % 360;
  }
  return h;
}

export function avatarStyle(label: string): { backgroundColor: string; color: string } {
  const hue = pseudonymHue(label || "?");
  return {
    backgroundColor: `hsl(${hue} 55% 32%)`,
    color: "hsl(0 0% 96%)",
  };
}

export function initialsFromPseudonym(label: string): string {
  const t = label.trim();
  if (!t) return "?";
  const parts = t.split(/[\s_-]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return t.slice(0, 2).toUpperCase();
}
