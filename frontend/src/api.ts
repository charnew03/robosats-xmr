export type Offer = {
  offer_id: string;
  maker_id: string;
  amount_xmr: number;
  premium_pct: number;
  fiat_currency: string;
  payment_method: string;
  maker_bond_amount: number;
  taker_bond_amount: number;
  is_active: boolean;
  taken_by: string | null;
  trade_id: string | null;
  created_at: string;
  updated_at: string;
};

/** Subset of trade fields returned after taking an offer. */
export type Trade = {
  trade_id: string;
  state: string;
  amount_xmr: number;
  seller_id: string;
  buyer_id: string | null;
  deposit_address: string | null;
  required_confirmations: number;
  current_confirmations: number;
  maker_bond_amount: number;
  taker_bond_amount: number;
};

export type TakeOfferBody = {
  taker_id: string;
  required_confirmations?: number;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function getOffers(signal?: AbortSignal): Promise<Offer[]> {
  const response = await fetch(`${API_BASE_URL}/offers`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Failed to load offers (${response.status})`);
  }

  return (await response.json()) as Offer[];
}

export async function takeOffer(
  offerId: string,
  body: TakeOfferBody,
  signal?: AbortSignal,
): Promise<Trade> {
  const response = await fetch(`${API_BASE_URL}/offers/${encodeURIComponent(offerId)}/take`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      taker_id: body.taker_id,
      required_confirmations: body.required_confirmations ?? 10,
    }),
    signal,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const err = (await response.json()) as { detail?: string | unknown };
      if (typeof err.detail === "string") detail = err.detail;
      else if (Array.isArray(err.detail)) detail = JSON.stringify(err.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }

  return (await response.json()) as Trade;
}
