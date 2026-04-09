import type { Offer } from "../api";
import { formatFiatCurrency, formatPremium, formatXmr, shortId } from "../lib/format";

type Props = {
  offer: Offer;
  onTake: (offer: Offer) => void;
};

/** Mobile-friendly row: full-width Take button (no horizontal table scroll). */
export function OfferRowCard({ offer, onTake }: Props) {
  return (
    <article className="rounded-lg border border-xmr-border bg-black/20 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="rounded bg-emerald-950/60 px-2 py-0.5 text-xs text-emerald-200">Sell XMR</span>
        <span className="font-mono text-lg font-semibold">{formatXmr(offer.amount_xmr)} XMR</span>
      </div>
      <p className="mt-2 text-sm text-xmr-muted">
        {formatPremium(offer.premium_pct)} · {formatFiatCurrency(offer.fiat_currency)} ·{" "}
        {offer.payment_method}
      </p>
      <p className="mt-1 font-mono text-xs text-xmr-muted" title={offer.maker_id}>
        Maker {shortId(offer.maker_id)}
      </p>
      <p className="mt-1 text-xs text-xmr-muted">
        Bonds M/T: {formatXmr(offer.maker_bond_amount)} / {formatXmr(offer.taker_bond_amount)} XMR
      </p>
      <button
        type="button"
        onClick={() => onTake(offer)}
        className="mt-4 w-full rounded-md bg-xmr-accent py-3 text-sm font-semibold text-black hover:bg-xmr-accentSoft"
      >
        Take this offer
      </button>
    </article>
  );
}
