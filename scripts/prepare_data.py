"""Raw Kaggle CSV -> data/processed/pitches.jsonl (anonymized cards + outcomes).

    python scripts/prepare_data.py data/raw/shark_tank_us.csv
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import PROCESSED  # noqa: E402
from tank.columns import SHARKS  # noqa: E402
from tank.data import load_csv, save_jsonl, seen_by  # noqa: E402
from tank.enrich import enrich  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default=str(PROCESSED))
    args = ap.parse_args()

    records, cols = load_csv(args.csv)
    report = enrich(records, Path(args.csv).resolve().parent)
    save_jsonl(records, Path(args.out))
    print("Enrichment:", json.dumps({k: v for k, v in report.items() if k != "wikipedia_revisions"}))

    optional = [f for f in ("yearly_revenue", "gross_margin", "air_date", "valuation") if f in cols]
    print(f"{len(records)} pitches, seasons {min(r['season'] for r in records)}-{max(r['season'] for r in records)}")
    print(f"Optional fields found: {optional or 'none'}")
    if "yearly_revenue" not in cols:
        print("WARNING: no revenue column. Cards will lack sales numbers, which Sharks lean on heavily.")
    for slug, name in SHARKS.items():
        seen = seen_by(records, slug)
        deals = sum(1 for r in seen if r["outcome"]["per_shark"][slug]["invested"])
        print(f"  {name:18s} seen {len(seen):5d}  invested {deals:4d}  ({deals / max(len(seen), 1):.1%})")
    leaks = [r["pitch_id"] for r in records if r["secret"]["name"] and r["secret"]["name"].lower() in r["card"]["description"].lower()]
    print(f"Cards still containing the company name: {len(leaks)} {leaks[:10]}")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
