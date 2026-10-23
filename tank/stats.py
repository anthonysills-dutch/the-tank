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

    return {
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
