"""Run the backtest and the memorization probe inside Claude Code, on the user's plan. No API key, no API bill.

The scripts here do all the bookkeeping; Claude Code subagents only judge. The /tank-eval skill drives it:

    python eval/claude_code.py prepare backtest --shark cuban --test-on 7-8
    python eval/claude_code.py prepare probe --test-on 7-8
        -> eval/work/<job>/instructions.md, batch-NN.md   (what the subagents read)
           eval/work/<job>/key.json                      (item -> pitch_id; the subagents never see it)
    ... one subagent per batch writes eval/work/<job>/out-NN.jsonl ...
    python eval/claude_code.py collect backtest --shark cuban
    python eval/claude_code.py collect probe
        -> eval/results/llm_<shark>_claude-code.jsonl and memorization_claude-code.jsonl,
           the same format run_llm.py writes, so score.py works unchanged:
    python eval/score.py --shark cuban --model claude-code

Leakage rules are the same as run_llm.py: train-split stats and precedents only, anonymized cards,
and items carry opaque ids (real pitch ids encode season and episode).
"""

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.probe_memorization import SCHEMA as PROBE_SCHEMA  # noqa: E402
from eval.probe_memorization import SYSTEM as PROBE_SYSTEM  # noqa: E402
from eval.probe_memorization import name_match  # noqa: E402
from eval.run_llm import build  # noqa: E402
from tank import PROCESSED, ROOT  # noqa: E402
from tank.data import load_jsonl, parse_seasons, seen_by, split  # noqa: E402
from tank.profiles import sourced_slugs  # noqa: E402
from tank.prompt import VERDICT_SCHEMA, card_text  # noqa: E402

WORK = ROOT / "eval" / "work"
RESULTS = ROOT / "eval" / "results"
MODEL_TAG = "claude-code"


def job_dir(kind, shark=None):
    return WORK / (f"backtest-{shark}" if kind == "backtest" else "probe")


def instructions(kind, system, schema):
    task = ("judge each pitch as the investor described below" if kind == "backtest"
            else "say whether you recognize each anonymized pitch")
    return "\n".join([
        f"# Task: {task}",
        "",
        "You are one of several evaluators working through batches. Rules:",
        "- Read only this file and the one batch file you were given. Do not open any other file in the repo.",
        "- Do not use web search, web fetch, or any tool except Read and Write.",
        "- Treat every item independently. Earlier items in the batch must not change how you judge later ones.",
        "- For every item, write one JSON object per line to the output file named in your batch:",
        '  {"item": "<item id>", "answer": { ...object matching the schema... }}',
        "- Write the whole file once, after you have judged every item. No other text in the file.",
        "",
        "## Instructions for each item",
        "",
        system,
        "",
        "## Answer schema",
        "```json",
        json.dumps(schema, indent=2),
        "```",
        "",
    ])


def prepare(args):
    records = load_jsonl(args.data)
    test_on = parse_seasons(args.test_on)
    if args.kind == "backtest":
        system, jobs = build(records, args.shark, args.test_seasons, test_on)
        items = [(r["pitch_id"], user) for r, user in jobs]
        schema = VERDICT_SCHEMA
    else:
        ids = {r["pitch_id"] for s in sourced_slugs() for r in split(seen_by(records, s), args.test_seasons, test_on)[1]}
        system, schema = PROBE_SYSTEM, PROBE_SCHEMA
        items = [(r["pitch_id"], "## The pitch\n" + card_text(r["card"])) for r in records if r["pitch_id"] in ids]

    rng = random.Random(5)
    rng.shuffle(items)  # so batch order says nothing about season or episode
    d = job_dir(args.kind, args.shark)
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "instructions.md").write_text(instructions(args.kind, system, schema), encoding="utf-8")
    key, batches = {}, []
    for b, start in enumerate(range(0, len(items), args.batch_size), 1):
        chunk = items[start:start + args.batch_size]
        lines = [f"# Batch {b:02d}", "", f"Output file: {(d / f'out-{b:02d}.jsonl').as_posix()}", ""]
        for i, (pitch_id, text) in enumerate(chunk, 1):
            item = f"b{b:02d}-{i:02d}"
            key[item] = pitch_id
            lines += [f"---", f"ITEM {item}", "", text, ""]
        (d / f"batch-{b:02d}.md").write_text("\n".join(lines), encoding="utf-8")
        batches.append(b)
    (d / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    print(f"{len(items)} items in {len(batches)} batches under {d.relative_to(ROOT).as_posix()}")
    print("Spawn one subagent per batch (see .claude/skills/tank-eval/SKILL.md), then run collect.")


def _valid_verdict(a):
    try:
        ok = a["decision"] in {"in", "out"} and 0.0 <= float(a["p_invest"]) <= 1.0
        return ok and all(k in a for k in VERDICT_SCHEMA["required"])
    except (KeyError, TypeError, ValueError):
        return False


def collect(args):
    d = job_dir(args.kind, args.shark)
    key = json.loads((d / "key.json").read_text(encoding="utf-8"))
    answers, bad = {}, []
    for out in sorted(d.glob("out-*.jsonl")):
        for n, line in enumerate(out.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                answers[row["item"]] = row["answer"]
            except (json.JSONDecodeError, KeyError, TypeError):
                bad.append(f"{out.name}:{n}")
    missing = [i for i in key if i not in answers]

    RESULTS.mkdir(parents=True, exist_ok=True)
    records = {r["pitch_id"]: r for r in load_jsonl(args.data)}
    if args.kind == "backtest":
        path = RESULTS / f"llm_{args.shark}_{MODEL_TAG}.jsonl"
        with open(path, "w", encoding="utf-8") as fh:
            for item, pitch_id in key.items():
                a = answers.get(item)
                row = {"pitch_id": pitch_id, "shark": args.shark, "model": MODEL_TAG}
                if a is not None and _valid_verdict(a):
                    row.update(verdict=a, error=None)
                else:
                    row["error"] = "missing" if a is None else "invalid"
                fh.write(json.dumps(row) + "\n")
    else:
        path = RESULTS / f"memorization_{MODEL_TAG}.jsonl"
        with open(path, "w", encoding="utf-8") as fh:
            for item, pitch_id in key.items():
                a = answers.get(item)
                row = {"pitch_id": pitch_id, "error": None if a else "missing"}
                if a:
                    row.update(a)
                    row["match"] = bool(a.get("recognized") and name_match(a.get("company_name"), records[pitch_id]["secret"]["name"]))
                fh.write(json.dumps(row) + "\n")
    print(f"{len(key) - len(missing)}/{len(key)} answered; {len(bad)} unparseable lines {bad[:5]}; "
          f"missing batches: {sorted({i[:3] for i in missing})}")
    print(f"Wrote {path.relative_to(ROOT).as_posix()}")


def status(args):
    d = job_dir(args.kind, args.shark)
    batches = sorted(p.stem.split("-")[1] for p in d.glob("batch-*.md"))
    done = {p.stem.split("-")[1] for p in d.glob("out-*.jsonl")}
    print(f"{len(done)}/{len(batches)} batches have output. To do: {[b for b in batches if b not in done]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["prepare", "collect", "status"])
    ap.add_argument("kind", choices=["backtest", "probe"])
    ap.add_argument("--shark")
    ap.add_argument("--test-seasons", type=int, default=3)
    ap.add_argument("--test-on")
    ap.add_argument("--batch-size", type=int, default=15)
    ap.add_argument("--data", default=str(PROCESSED))
    args = ap.parse_args()
    if args.kind == "backtest" and not args.shark:
        ap.error("backtest needs --shark")
    {"prepare": prepare, "collect": collect, "status": status}[args.action](args)


if __name__ == "__main__":
    main()
