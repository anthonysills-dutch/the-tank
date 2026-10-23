"""Can a blind judge tell the Sharks apart from their critiques alone?

    python eval/distinctiveness.py --model claude-opus-5-5 --n 40          # dry run + estimate
    python eval/distinctiveness.py --model claude-opus-5-5 --n 40 --yes

Reuses critiques already produced by run_llm.py (no new verdicts are generated), strips the
decision and offer, and asks a judge which investor lens wrote each one. Needs at least two
sourced Sharks backtested on overlapping pitches. Chance is 1/k; well above chance means the
personas did not collapse into one generic "AI investor".
"""

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.llm import call_json, client, gate  # noqa: E402
from tank import ROOT  # noqa: E402
from tank.profiles import load, sourced_slugs  # noqa: E402

RESULTS = ROOT / "eval" / "results"


def critique(v):
    return "\n".join(["Objections:"] + [f"- {o}" for o in v["objections"]] +
                     [f"Hardest question: {v['grill_question']}", f"Reasoning: {v['reasoning']}"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5-5", help="Model whose run_llm critiques to judge (also the judge)")
    ap.add_argument("--n", type=int, default=40, help="Pitches to sample")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    slugs = sourced_slugs()
    by_pitch = defaultdict(dict)
    for slug in slugs:
        path = RESULTS / f"llm_{slug}_{args.model}.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines() if path.exists() else []:
            row = json.loads(line)
            if row.get("verdict"):
                by_pitch[row["pitch_id"]][slug] = row["verdict"]
    shared = [p for p, d in by_pitch.items() if len(d) >= 2]
    if len(slugs) < 2 or not shared:
        raise SystemExit("Need >= 2 sourced Sharks with backtest critiques on the same pitches.")

    rng = random.Random(11)
    pitches = rng.sample(shared, min(args.n, len(shared)))
    lenses = {s: load(s)["lens"] for s in slugs}
    options = "\n".join(f"- {s}: {lens}" for s, lens in lenses.items())
    system = ("You will read one investor's critique of a startup pitch. Decide which investor lens most likely wrote it. "
              f"Options:\n{options}")
    schema = {"type": "object", "properties": {"investor": {"type": "string", "enum": slugs}},
              "required": ["investor"], "additionalProperties": False}
    jobs = [(p, s, critique(v)) for p in pitches for s, v in by_pitch[p].items()]
    gate(args.model, [(system, c) for _, _, c in jobs], args.yes, "Distinctiveness judge")

    c = client()
    confusion = defaultdict(Counter)
    for p, truth, text in jobs:
        data, err, _ = call_json(c, args.model, system, text, schema, effort="low", max_tokens=2000)
        confusion[truth][data["investor"] if data else "error"] += 1
    total = sum(sum(v.values()) for v in confusion.values())
    correct = sum(confusion[s][s] for s in slugs)
    print(f"Attribution accuracy {correct}/{total} = {correct / total:.1%} (chance {1 / len(slugs):.1%})")
    for s in slugs:
        print(f"  {s:10s} -> {dict(confusion[s])}")


if __name__ == "__main__":
    main()
