"""Memorization probe: can the model name the company from the anonymized card alone?

    python eval/probe_memorization.py --model claude-opus-5-5          # dry run + estimate
    python eval/probe_memorization.py --model claude-opus-5-5 --yes

If it can, any verdict it gives on that pitch may be recall, not judgment. score.py reports
results separately for recognized and unrecognized pitches; the pass gate uses unrecognized only.
Run this with the same model you backtest.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.llm import call_json, client, gate  # noqa: E402
from tank import PROCESSED, ROOT  # noqa: E402
from tank.data import load_jsonl, parse_seasons, seen_by, split  # noqa: E402
from tank.profiles import sourced_slugs  # noqa: E402
from tank.prompt import card_text  # noqa: E402

RESULTS = ROOT / "eval" / "results"

SYSTEM = (
    "You will see an anonymized pitch from a US TV show where entrepreneurs pitch investors. "
    "If you recognize the specific company, name it and say what you remember about how the pitch went. "
    "If you do not recognize it, say so. Do not guess a plausible-sounding name."
)
SCHEMA = {
    "type": "object",
    "properties": {
        "recognized": {"type": "boolean"},
        "company_name": {"type": ["string", "null"]},
        "remembered_outcome": {"type": ["string", "null"]},
    },
    "required": ["recognized", "company_name", "remembered_outcome"],
    "additionalProperties": False,
}


def _norm_tokens(s):
    return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in {"the", "inc", "llc", "co"}}


def name_match(guess, truth):
    g, t = _norm_tokens(guess), _norm_tokens(truth)
    if not g or not t:
        return False
    if "".join(sorted(g)) == "".join(sorted(t)):
        return True
    gs, ts = re.sub(r"[^a-z0-9]", "", guess.lower()), re.sub(r"[^a-z0-9]", "", truth.lower())
    if len(ts) >= 4 and (ts in gs or gs in ts):
        return True
    return len(g & t) / len(g | t) >= 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--test-seasons", type=int, default=3)
    ap.add_argument("--test-on", help="Probe these seasons' pitches, e.g. 7,8 (match the backtest)")
    ap.add_argument("--all-seasons", action="store_true", help="Probe every pitch, not just the test split")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()

    records = load_jsonl(PROCESSED)
    if args.all_seasons:
        targets = records
    else:
        # The union of every sourced Shark's test split, so each backtested pitch gets probed.
        ids = {r["pitch_id"] for s in sourced_slugs() for r in split(seen_by(records, s), args.test_seasons, parse_seasons(args.test_on))[1]}
        targets = [r for r in records if r["pitch_id"] in ids]
    out = RESULTS / f"memorization_{args.model}.jsonl"
    done = {json.loads(l)["pitch_id"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    todo = [r for r in targets if r["pitch_id"] not in done][: args.limit]
    gate(args.model, [(SYSTEM, card_text(r["card"])) for r in todo], args.yes, "Memorization probe")

    c = client()
    RESULTS.mkdir(parents=True, exist_ok=True)
    with open(out, "a", encoding="utf-8") as fh:
        for i, r in enumerate(todo, 1):
            data, err, _ = call_json(c, args.model, SYSTEM, card_text(r["card"]), SCHEMA, effort=args.effort, max_tokens=4000)
            row = {"pitch_id": r["pitch_id"], "error": err}
            if data:
                row.update(data)
                row["match"] = bool(data["recognized"] and name_match(data.get("company_name"), r["secret"]["name"]))
            fh.write(json.dumps(row) + "\n")
            print(f"[{i}/{len(todo)}] {r['pitch_id']} {'RECOGNIZED' if row.get('match') else ('error ' + err if err else 'unknown')}")


if __name__ == "__main__":
    main()
