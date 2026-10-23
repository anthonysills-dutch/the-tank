"""Keep sharks/profile.schema.json in step with tank/profiles.py and the real profiles. No network.

    python -m unittest discover tests
"""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import SHARKS_DIR  # noqa: E402
from tank.columns import SHARKS  # noqa: E402
from tank.profiles import CONFIDENCE, KINDS, WEIGHTS, load_raw  # noqa: E402

SCHEMA = json.loads((SHARKS_DIR / "profile.schema.json").read_text(encoding="utf-8"))
PROPS = SCHEMA["properties"]


def item_props(key):
    return PROPS[key]["items"]["properties"]


class Schema(unittest.TestCase):
    def test_enums_match_the_validator(self):
        self.assertEqual(set(PROPS["slug"]["enum"]), set(SHARKS))
        self.assertEqual(set(item_props("beliefs")["weight"]["enum"]), WEIGHTS)
        self.assertEqual(set(item_props("beliefs")["confidence"]["enum"]), CONFIDENCE)
        self.assertEqual(set(item_props("sources")["kind"]["enum"]), KINDS)

    def test_profiles_use_only_declared_keys(self):
        quote_keys = set(SCHEMA["$defs"]["quote"]["properties"])
        for slug in SHARKS:
            if not (SHARKS_DIR / slug / "profile.toml").exists():
                continue
            p = load_raw(slug)
            self.assertLessEqual(set(p), set(PROPS), slug)
            self.assertLessEqual(set(SCHEMA["required"]), set(p), slug)
            for key in ("beliefs", "misfires", "dealbreakers", "sources"):
                spec = PROPS[key]["items"]
                for entry in p.get(key, []):
                    self.assertLessEqual(set(entry), set(spec["properties"]), f"{slug}/{key}")
                    self.assertLessEqual(set(spec["required"]), set(entry), f"{slug}/{key}")
                    for q in entry.get("quotes", []):
                        self.assertEqual(set(q), quote_keys, f"{slug}/{key} quote")


if __name__ == "__main__":
    unittest.main()
