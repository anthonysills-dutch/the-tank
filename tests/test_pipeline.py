"""End-to-end checks on synthetic data. No network, no API key.

    python -m unittest discover tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval import baselines  # noqa: E402
from eval.probe_memorization import name_match  # noqa: E402
from scripts import build_agents  # noqa: E402
from tank.data import anonymize, load_csv, save_jsonl, seen_by, split  # noqa: E402
from tank.precedents import opaque_id, retrieve  # noqa: E402
from tank.profiles import ProfileError, load, sourced_slugs, validate  # noqa: E402
from tank.quotes import found, norm  # noqa: E402
from tank.prompt import pitch_message, system_prompt  # noqa: E402
from tank.stats import shark_stats  # noqa: E402
from tests.fixture import write_fixture  # noqa: E402


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        write_fixture(cls.tmp / "raw.csv")
        cls.records, cls.cols = load_csv(cls.tmp / "raw.csv")
        cls.processed = cls.tmp / "pitches.jsonl"
        save_jsonl(cls.records, cls.processed)

    def test_cards_are_anonymized(self):
        for r in self.records:
            text = r["card"]["description"].lower()
            self.assertNotIn(r["secret"]["name"].lower(), text)
            self.assertNotIn("quentin", text)
            self.assertNotIn(".com", text)
            self.assertNotIn("season", r["card"])
            self.assertNotIn("air_date", r["card"])

    def test_anonymize_handles_partial_names(self):
        out = anonymize("Scrub Daddy is a sponge. The Daddy grip by Aaron Krause.", "Scrub Daddy", "Aaron Krause", "")
        self.assertNotIn("Daddy", out)
        self.assertNotIn("Krause", out)

    def test_parses_money_and_percent(self):
        r = self.records[0]
        self.assertIsInstance(r["card"]["ask_amount"], float)
        self.assertIsInstance(r["card"]["ask_equity_pct"], float)

    def test_absent_shark_excluded(self):
        s1 = [r for r in self.records if r["season"] == 1]
        self.assertFalse(any(r in seen_by(s1, "john") for r in s1))

    def test_split_is_time_ordered(self):
        train, test = split(self.records, 3)
        self.assertLess(max(r["season"] for r in train), min(r["season"] for r in test))

    def test_precedents_come_only_from_pool(self):
        train, test = split(self.records, 3)
        train_ids = {r["pitch_id"] for r in train}
        precs = retrieve(test[0]["card"], train, "cuban", k=6)
        self.assertTrue(precs)
        self.assertTrue(all(p["precedent_id"] in {opaque_id(i) for i in train_ids} for p in precs))

    def test_precedent_ids_hide_season(self):
        train, test = split(self.records, 3)
        for p in retrieve(test[0]["card"], train, "cuban"):
            self.assertNotRegex(p["precedent_id"], r"S\d\dE\d\d")

    def test_baselines_logistic_learns_revenue_signal(self):
        report = baselines.run(self.records, "cuban", 3)
        m = report["metrics"]
        self.assertLess(m["logistic"]["brier"], m["base_rate"]["brier"])
        self.assertEqual(m["always_out"]["f1_in"], 0.0)

    def test_cuban_profile_is_sourced_and_renders(self):
        self.assertEqual(sorted(sourced_slugs()), sorted(["cuban", "oleary", "corcoran", "greiner", "herjavec", "john"]))
        profile = load("cuban")
        train, test = split(self.records, 3)
        sys_prompt = system_prompt(profile, shark_stats(train, "cuban"))
        self.assertIn("[sales-cure-all]", sys_prompt)
        self.assertIn("not the person", sys_prompt)
        msg = pitch_message(test[0]["card"], retrieve(test[0]["card"], train, "cuban"))
        self.assertNotIn(test[0]["secret"]["name"], msg)

    def test_belief_without_quote_rejected(self):
        src = [{"id": "s1", "url": "https://x", "kind": "own-writing"}]
        mis = [{"claim": "c", "quotes": []}]
        belief = {"id": "x", "claim": "y", "weight": "core", "confidence": "own-writing"}
        with self.assertRaises(ProfileError):
            validate({"slug": "cuban", "status": "sourced", "sources": src, "misfires": mis, "beliefs": [belief]}, "cuban")
        belief["quotes"] = [{"text": "a real quote here", "source": "nope"}]
        with self.assertRaises(ProfileError):
            validate({"slug": "cuban", "status": "sourced", "sources": src, "misfires": mis, "beliefs": [belief]}, "cuban")
        belief["quotes"] = [{"text": "a real quote here", "source": "s1"}]
        validate({"slug": "cuban", "status": "sourced", "sources": src, "misfires": mis, "beliefs": [belief]}, "cuban")

    def test_quote_matching_is_verbatim(self):
        hay = norm("He said: Sales cures all. No business has ever succeeded without sales.")
        self.assertTrue(found("Sales cures all. No business has ever succeeded without sales.", hay))
        self.assertTrue(found("sales cures all ... has ever succeeded", hay))
        self.assertFalse(found("Sales cures everything. No business has ever succeeded without sales.", hay))
        self.assertFalse(found("No business has succeeded without sales.", hay))

    def test_build_agents_only_sourced(self):
        out = self.tmp / "agents"
        build_agents.main(self.processed, out)
        self.assertEqual(len(list(out.iterdir())), 6)
        text = (out / "shark-cuban.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: shark-cuban\n"))

    def test_customer_docs_pass_ste_lint(self):
        from scripts.ste_check import check
        docs = sorted((Path(__file__).resolve().parent.parent / "package_src").rglob("*.md"))
        self.assertTrue(docs)
        self.assertEqual([(d.name, p) for d in docs for p in check(d)], [])

    def test_name_match(self):
        self.assertTrue(name_match("Scrub Daddy Inc.", "Scrub Daddy"))
        self.assertTrue(name_match("ScrubDaddy", "Scrub Daddy"))
        self.assertFalse(name_match("Bombas", "Scrub Daddy"))
        self.assertFalse(name_match(None, "Scrub Daddy"))


if __name__ == "__main__":
    unittest.main()
