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
