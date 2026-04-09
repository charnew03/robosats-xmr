/** Local-only notes for offers (API has no description field yet). */
const PREFIX = "robosats_xmr_offer_note_v1_";

export function saveOfferNote(offerId: string, note: string): void {
  const t = note.trim();
  if (!t) {
    localStorage.removeItem(PREFIX + offerId);
    return;
  }
  localStorage.setItem(PREFIX + offerId, t);
}

export function loadOfferNote(offerId: string): string {
  return localStorage.getItem(PREFIX + offerId) ?? "";
}
