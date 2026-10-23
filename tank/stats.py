"""Behavior derived from a Shark's deal record.

Always call this on the training split during a backtest. Computing it on all data leaks the test set.
"""

from collections import Counter
from statistics import median

from .data import seen_by

MIN_INDUSTRY_N = 8


def shark_stats(records, slug):
    seen = seen_by(records, slug)
    deals = [r for r in seen if r["outcome"]["per_shark"][slug]["invested"]]
    amounts = [r["outcome"]["per_shark"][slug]["amount"] for r in deals if r["outcome"]["per_shark"][slug]["amount"]]
    equities = [r["outcome"]["per_shark"][slug]["equity_pct"] for r in deals if r["outcome"]["per_shark"][slug]["equity_pct"]]
    asked = [r["card"]["ask_equity_pct"] for r in deals if r["card"]["ask_equity_pct"]]

    seen_by_ind = Counter(r["card"]["industry"] for r in seen if r["card"]["industry"])
    deal_by_ind = Counter(r["card"]["industry"] for r in deals if r["card"]["industry"])
    overall = len(deals) / len(seen) if seen else 0.0
    industries = sorted(
        (
            {"industry": ind, "seen": n, "invest_rate": round(deal_by_ind[ind] / n, 3)}
            for ind, n in seen_by_ind.items() if n >= MIN_INDUSTRY_N
        ),
        key=lambda d: d["invest_rate"],
        reverse=True,
    )
    solo = [r for r in deals if r["outcome"]["per_shark"] and sum(
        1 for s in r["outcome"]["per_shark"].values() if s["invested"]) == 1]

    # Negotiation behavior, for Tank mode. Deal valuation / the founder's asked valuation: below 1 means the
    # Shark took more equity for the money than the founder offered.
    ratios = []
    for r in deals:
        s, ask_v = r["outcome"]["per_shark"][slug], r["card"].get("implied_valuation")
        if s["amount"] and s["equity_pct"] and ask_v:
            ratios.append((s["amount"] / (s["equity_pct"] / 100)) / ask_v)
    partners = Counter(other for r in deals for other, s in r["outcome"]["per_shark"].items()
                       if other != slug and s["invested"])
    shared = len(deals) - len(solo)

    return {
        "median_valuation_vs_ask": round(median(ratios), 2) if ratios else None,
        "valuation_ratio_n": len(ratios),
        "paid_full_ask_share": round(sum(1 for x in ratios if x >= 0.95) / len(ratios), 3) if ratios else None,
        "partners": [{"shark": k, "deals_together": v, "share_of_shared_deals": round(v / shared, 3)}
                     for k, v in partners.most_common()] if shared else [],
        "pitches_seen": len(seen),
        "deals": len(deals),
        "invest_rate": round(overall, 3),
        "median_amount": median(amounts) if amounts else None,
        "median_equity_pct": median(equities) if equities else None,
        "median_equity_founders_offered_in_these_deals": median(asked) if asked else None,
        "solo_deal_share": round(len(solo) / len(deals), 3) if deals else None,
        "royalty_deal_share": round(
            sum(1 for r in deals if r["outcome"]["royalty"]) / len(deals), 3) if deals else None,
        "most_receptive_industries": industries[:5],
        "least_receptive_industries": industries[5:][-5:][::-1],
    }
