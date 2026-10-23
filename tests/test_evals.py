"""Checks on the scoring code: synthetic data only, no network, no API key.

    python -m unittest discover tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.consistency import consistency, gate, pairs_from, signal  # noqa: E402
from eval.critique_checks import check, invented_numbers  # noqa: E402
from tank.metrics import auc, calibration_bins, summarize  # noqa: E402
from tank.profiles import load  # noqa: E402


def verdict(decision="out", p=0.1, **kw):
    v = {"decision": decision, "p_invest": p,
         "offer": {"amount_usd": None, "equity_pct": None, "royalty": None, "loan_usd": None, "conditions": []},
         "objections": ["No sales shown.", "Margin unknown.", "Crowded market."],
         "grill_question": "What did you sell last month?",
         "reasoning": "Sales come first. This pitch shows none.", "evidence": ["sales-cure-all", "P-abc123"]}
    v.update(kw)
    return v


CARD = {"industry": "Food", "description": "Sauce that sells for $8 a jar, 40% repeat buyers.",
        "ask_amount": 100000, "ask_equity_pct": 10, "implied_valuation": 1000000, "team": "solo founder"}


class Metrics(unittest.TestCase):
    def test_auc(self):
        self.assertEqual(auc([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1]), 1.0)
        self.assertEqual(auc([1, 0], [0.5, 0.5]), 0.5)
        self.assertIsNone(auc([0, 0], [0.1, 0.2]))

    def test_threshold_changes_f1_not_brier(self):
        y, p = [1, 0, 0, 0, 0], [0.3, 0.1, 0.1, 0.1, 0.1]
        at_half, at_rate = summarize(y, p, 0.5), summarize(y, p, 0.2)
        self.assertEqual(at_half["f1_in"], 0.0)
        self.assertEqual(at_rate["f1_in"], 1.0)
        self.assertEqual(at_half["brier"], at_rate["brier"])

    def test_calibration_bins_cover_all(self):
        bins = calibration_bins([0, 1, 0, 1, 1, 0, 0], [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
        self.assertEqual(sum(b["n"] for b in bins), 7)


class Consistency(unittest.TestCase):
    def test_signal(self):
        self.assertEqual(signal(0.31, 0.2), "ABOVE")
        self.assertEqual(signal(0.10, 0.2), "BELOW")
        self.assertEqual(signal(0.20, 0.2), "USUAL")

    def test_pairs_and_gate(self):
        rows = []
        for i in range(25):
            rows.append({"pitch_id": f"x{i}", "run": 1, "verdict": verdict(p=0.10)})
            rows.append({"pitch_id": f"x{i}", "run": 2, "verdict": verdict(p=0.12)})
        rows.append({"pitch_id": "lonely", "run": 1, "verdict": verdict()})
        pairs = pairs_from(rows)
        self.assertEqual(len(pairs), 25)
        m = consistency(pairs, rate=0.18)
        self.assertEqual(m["decision_agreement"], 1.0)
        self.assertEqual(gate(m)[0], "PASS")
        flipped = [(pid, a, verdict("in", 0.5, offer={"amount_usd": 1, "equity_pct": 1, "royalty": None,
                                                       "loan_usd": None, "conditions": []}))
                   for pid, a, _ in pairs]
        self.assertEqual(gate(consistency(flipped, 0.18))[0], "FAIL")


class CritiqueChecks(unittest.TestCase):
    def setUp(self):
        self.profile = load("cuban")

    def test_clean_verdict_passes(self):
        res = check(verdict(), CARD, self.profile)
        self.assertTrue(all(v is None for v in res.values()), res)

    def test_numbers_on_the_card_are_allowed(self):
        self.assertEqual(invented_numbers("At $1M valuation, $8 a jar and 40% repeat, 10% is fair.", CARD, verdict()), [])
        self.assertEqual(invented_numbers("You need $5M in sales.", CARD, verdict()), ["$5M"])

    def test_failures_are_caught(self):
        bad = verdict(evidence=["not-a-belief"], objections=["Same.", "Same.", "Same."], grill_question="Tell me more.",
                      reasoning='As I always say "this line was never said by anyone at all".')
        res = check(bad, CARD, self.profile)
        for c in ("evidence", "quotes", "structure"):
            self.assertIsNotNone(res[c], c)
        self.assertIsNotNone(check(verdict("in"), CARD, self.profile)["offer"])


class TankMode(unittest.TestCase):
    def test_negotiation_only_in_shipped_agents(self):
        from tank.prompt import MOVE_SCHEMA, system_prompt
        stats = {"deals": 2, "pitches_seen": 10, "invest_rate": 0.2, "median_valuation_vs_ask": 0.6,
                 "paid_full_ask_share": 0.2, "partners": [{"shark": "greiner", "deals_together": 3}]}
        profile = load("cuban")
        self.assertNotIn("TANK MODE", system_prompt(profile, stats))  # the backtest prompt is unchanged
        agent = system_prompt(profile, stats, negotiation=True)
        self.assertIn("TANK MODE", agent)
        self.assertIn("greiner (3)", agent)
        self.assertIn("PARTNER", MOVE_SCHEMA["properties"]["move"]["enum"])

    def test_negotiation_stats(self):
        from tank.stats import shark_stats

        def rec(ask, eq, deal):
            per = {s: {"present": True, "invested": False, "amount": None, "equity_pct": None}
                   for s in ("cuban", "oleary", "corcoran", "greiner", "herjavec", "john")}
            for s, amount, equity in deal:
                per[s] = {"present": True, "invested": True, "amount": amount, "equity_pct": equity}
            return {"card": {"industry": "Food", "ask_amount": ask, "ask_equity_pct": eq,
                             "implied_valuation": ask / (eq / 100)},
                    "outcome": {"royalty": None, "per_shark": per}}

        records = [rec(100000, 10, [("cuban", 100000, 20)]),                        # half the asked valuation
                   rec(100000, 10, [("cuban", 50000, 5), ("greiner", 50000, 5)]),   # full ask, shared
                   rec(100000, 10, [])]
        s = shark_stats(records, "cuban")
        self.assertEqual(s["median_valuation_vs_ask"], 0.75)
        self.assertEqual(s["paid_full_ask_share"], 0.5)
        self.assertEqual(s["partners"][0]["shark"], "greiner")


if __name__ == "__main__":
    unittest.main()
