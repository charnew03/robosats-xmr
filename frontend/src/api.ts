const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function parseApiError(response: Response): Promise<string> {
  let detail = `HTTP ${response.status}`;
  try {
    const err = (await response.json()) as { detail?: string | unknown };
    if (typeof err.detail === "string") detail = err.detail;
    else if (Array.isArray(err.detail)) detail = JSON.stringify(err.detail);
  } catch {
    /* ignore */
  }
  return detail;
}

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

export type Trade = {
  trade_id: string;
  state: string;
  amount_xmr: number;
  seller_id: string;
  buyer_id: string | null;
  deposit_address: string | null;
  required_confirmations: number;
  current_confirmations: number;
  funded_at: string | null;
  buyer_payout_address: string | null;
  seller_refund_address: string | null;
  release_txid: string | null;
  refund_txid: string | null;
  dispute_reason: string | null;
  dispute_opened_at: string | null;
  maker_bond_address: string | null;
  taker_bond_address: string | null;
  maker_bond_amount: number;
  taker_bond_amount: number;
  maker_bond_confirmations: number;
  taker_bond_confirmations: number;
  deposit_subaddress_index: number | null;
  maker_bond_subaddress_index: number | null;
  taker_bond_subaddress_index: number | null;
};

export type CreateOfferBody = {
  maker_id: string;
  amount_xmr: number;
  premium_pct: number;
  fiat_currency: string;
  payment_method: string;
  maker_bond_amount_xmr: number;
  taker_bond_amount_xmr: number;
};

export type TakeOfferBody = {
  taker_id: string;
  required_confirmations?: number;
};

export async function getOffers(signal?: AbortSignal): Promise<Offer[]> {
  const response = await fetch(`${API_BASE_URL}/offers`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal,
  });
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Offer[];
}

export async function createOffer(body: CreateOfferBody, signal?: AbortSignal): Promise<Offer> {
  const response = await fetch(`${API_BASE_URL}/offers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Offer;
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
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade;
}

export async function getTrades(signal?: AbortSignal): Promise<Trade[]> {
  const response = await fetch(`${API_BASE_URL}/trades`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal,
  });
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade[];
}

export async function getTrade(tradeId: string, signal?: AbortSignal): Promise<Trade> {
  const response = await fetch(`${API_BASE_URL}/trades/${encodeURIComponent(tradeId)}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
    signal,
  });
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade;
}

export async function markFiatPaid(tradeId: string, signal?: AbortSignal): Promise<Trade> {
  const response = await fetch(
    `${API_BASE_URL}/trades/${encodeURIComponent(tradeId)}/mark-fiat-paid`,
    { method: "POST", headers: { "Content-Type": "application/json" }, signal },
  );
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade;
}

export type ReleaseEscrowBody = {
  buyer_payout_address: string;
  maker_return_address?: string | null;
  taker_return_address?: string | null;
};

export async function releaseEscrow(
  tradeId: string,
  body: ReleaseEscrowBody,
  signal?: AbortSignal,
): Promise<Trade> {
  const response = await fetch(
    `${API_BASE_URL}/trades/${encodeURIComponent(tradeId)}/release-escrow`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    },
  );
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade;
}

export async function openDispute(
  tradeId: string,
  reason: string,
  signal?: AbortSignal,
): Promise<Trade> {
  const response = await fetch(
    `${API_BASE_URL}/trades/${encodeURIComponent(tradeId)}/open-dispute`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
      signal,
    },
  );
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade;
}

export type CancelTradeBody = {
  actor_id: string;
  reason: string;
  maker_return_address?: string | null;
  taker_return_address?: string | null;
};

export async function cancelTrade(
  tradeId: string,
  body: CancelTradeBody,
  signal?: AbortSignal,
): Promise<Trade> {
  const response = await fetch(`${API_BASE_URL}/trades/${encodeURIComponent(tradeId)}/cancel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade;
}

export async function refreshFunding(tradeId: string, signal?: AbortSignal): Promise<Trade> {
  const response = await fetch(
    `${API_BASE_URL}/trades/${encodeURIComponent(tradeId)}/refresh-funding`,
    { method: "POST", headers: { "Content-Type": "application/json" }, signal },
  );
  if (!response.ok) throw new Error(await parseApiError(response));
  return (await response.json()) as Trade;
}
