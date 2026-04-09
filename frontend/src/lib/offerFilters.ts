import type { Offer } from "../api";

export type SideFilter = "all" | "buy" | "sell";

/**
 * Backend offers are maker sell-XMR-for-fiat listings. From a taker POV that is "buy XMR".
 * "Sell XMR" listings (maker buys XMR) are not in the API yet — filter returns none.
 */
export function offerMatchesSide(_offer: Offer, side: SideFilter): boolean {
  if (side === "all") return true;
  const isMakerSellXmr = true;
  if (side === "buy") return isMakerSellXmr;
  if (side === "sell") return !isMakerSellXmr;
  return true;
}

export function filterOffers(
  offers: Offer[],
  opts: {
    side: SideFilter;
    payment: string;
    amountMin: string;
    amountMax: string;
    premiumMax: string;
  },
): Offer[] {
  return offers.filter((offer) => {
    if (!offerMatchesSide(offer, opts.side)) return false;

    if (
      opts.payment &&
      !offer.payment_method.toLowerCase().includes(opts.payment.trim().toLowerCase())
    ) {
      return false;
    }

    const minAmount = opts.amountMin ? Number(opts.amountMin) : null;
    const maxAmount = opts.amountMax ? Number(opts.amountMax) : null;
    const maxPremium = opts.premiumMax ? Number(opts.premiumMax) : null;

    if (minAmount !== null && !Number.isNaN(minAmount) && offer.amount_xmr < minAmount) {
      return false;
    }
    if (maxAmount !== null && !Number.isNaN(maxAmount) && offer.amount_xmr > maxAmount) {
      return false;
    }
    if (
      maxPremium !== null &&
      !Number.isNaN(maxPremium) &&
      offer.premium_pct > maxPremium
    ) {
      return false;
    }

    return true;
  });
}
