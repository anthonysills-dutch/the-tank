"""Backtest a Shark model on the held-out seasons.

    python eval/run_llm.py --shark cuban --dry-run          # print one prompt + cost estimate
    python eval/run_llm.py --shark cuban --limit 50 --yes   # spend

Leakage rules this enforces:
  - deal stats in the system prompt come from the training seasons only
  - precedents are drawn from the training seasons only
  - cards carry no names, dates or season numbers
Resumable: pitches already in the output file are skipped.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.llm import call_json, client, gate  # noqa: E402
from tank import PROCESSED, ROOT  # noqa: E402
from tank.data import load_jsonl, parse_seasons, seen_by, split  # noqa: E402
from tank.precedents import retrieve  # noqa: E402
from tank.profiles import load  # noqa: E402
from tank.prompt import VERDICT_SCHEMA, pitch_message, system_prompt  # noqa: E402
from tank.stats import shark_stats  # noqa: E402

RESULTS = ROOT / "eval" / "results"


def build(records, slug, test_seasons, test_on=None):
    profile = load(slug)
    if profile["status"] != "sourced":
        raise SystemExit(f"{slug} is a stub profile. Source it before backtesting.")
    train, test = split(seen_by(records, slug), test_seasons, test_on)
    system = system_prompt(profile, shark_stats(train, slug))
    jobs = [(r, pitch_message(r["card"], retrieve(r["card"], train, slug))) for r in test]
    return system, jobs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shark", required=True)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--test-seasons", type=int, default=3)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--test-on", help="Hold out these seasons instead, e.g. 7,8 (must match baselines.py)")
    ap.add_argument("--data", default=str(PROCESSED))
    args = ap.parse_args()

    system, jobs = build(load_jsonl(args.data), args.shark, args.test_seasons, parse_seasons(args.test_on))
    out = RESULTS / f"llm_{args.shark}_{args.model}.jsonl"
    done = {json.loads(l)["pitch_id"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    todo = [(r, u) for r, u in jobs if r["pitch_id"] not in done][: args.limit]

    if args.dry_run and todo:
        print("=== SYSTEM ===\n" + system + "\n\n=== FIRST PITCH ===\n" + todo[0][1] + "\n")
    gate(args.model, [(system, u) for _, u in todo], args.yes and not args.dry_run, f"Backtest {args.shark}")

    c = client()
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as fh:
        for i, (r, user) in enumerate(todo, 1):
            data, err, usage = call_json(c, args.model, system, user, VERDICT_SCHEMA, effort=args.effort)
            row = {"pitch_id": r["pitch_id"], "shark": args.shark, "model": args.model, "error": err, "usage": usage}
            if data:
                row["verdict"] = data
            fh.write(json.dumps(row) + "\n")
            tag = err or f"{data['decision']} p={data['p_invest']:.2f}"
            print(f"[{i}/{len(todo)}] {r['pitch_id']} {tag}")


if __name__ == "__main__":
    main()
