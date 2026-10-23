"""Grade the critique in Shark verdicts with a fixed rubric, using Claude Code subagents on the user's plan.

    python eval/rubric.py prepare --shark cuban --n 30          # samples verdicts from eval/results/llm_cuban_claude-code.jsonl
    ... one subagent per batch (the /tank-eval skill, step 3) reads eval/work/grade-cuban/ ...
    python eval/rubric.py status --shark cuban
    python eval/rubric.py collect --shark cuban                 # -> eval/results/rubric_cuban_claude-code.md

The grader sees the pitch card, the Shark's lens and beliefs, and the verdict. It never sees the real outcome:
the rubric grades the critique, not whether the decision matched the show.
Gate: every criterion averages >= 3.5 and the overall average is >= 4.0 (scale 1 to 5).
Limit: the grader is the same model family as the judge. Treat a PASS as necessary, not sufficient;
read the "worst flaw" lines yourself.
"""

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.claude_code import read_answers, write_batches  # noqa: E402
from tank import PROCESSED, ROOT  # noqa: E402
from tank.data import load_jsonl  # noqa: E402
from tank.profiles import load  # noqa: E402
from tank.prompt import card_text  # noqa: E402

RESULTS = ROOT / "eval" / "results"
WORK = ROOT / "eval" / "work"
CRITERIA = {
    "specificity": "Objections and reasoning use the facts on this pitch card. 1 = generic startup advice that fits "
                   "any pitch. 3 = mixes specific and generic. 5 = every point depends on a fact of this pitch.",
    "lens_fidelity": "The verdict judges through this investor's lens and beliefs, and the cited belief ids match the "
                     "argument. 1 = could be any investor. 3 = lens named but not applied. 5 = the lens drives the decision.",
    "actionability": "The founder can act on the objections and advice. 1 = vague. 3 = some steps are clear. "
                     "5 = each objection points to a concrete fix or proof the founder can bring.",
    "question_quality": "The hard question targets the weakest point of this pitch. 1 = generic or easy. "
                        "3 = relevant but not the crux. 5 = the one question that decides the deal.",
    "honesty": "No invented facts, no claimed knowledge of the real company or episode, missing facts treated as "
               "missing. 1 = invents facts. 3 = small overreach. 5 = every claim is on the card or in the profile.",
}
SCHEMA = {
    "type": "object",
    "properties": {**{c: {"type": "integer", "minimum": 1, "maximum": 5} for c in CRITERIA},
                   "worst_flaw": {"type": "string", "description": "One sentence: the biggest problem in this verdict."}},
    "required": list(CRITERIA) + ["worst_flaw"],
}
GATE_EACH, GATE_ALL = 3.5, 4.0


def job(shark):
    return WORK / f"grade-{shark}"


def instructions():
    lines = ["# Task: grade the critique in each investor verdict", "",
             "You are one of several graders working through batches. Rules:",
             "- Read only this file and the one batch file you were given. Do not open any other file.",
             "- Do not use web search, web fetch, or any tool except Read and Write.",
             "- Grade each item independently. Do not try to find out what really happened to the company.",
             "- Grade the critique, not the decision. An OUT can score 5. An IN can score 1.",
             "- For every item, write one JSON object per line to the output file named in your batch:",
             '  {"item": "<item id>", "answer": { ...object matching the schema... }}',
             "- Write the whole file once, after you have graded every item. No other text in the file.", "",
             "## Rubric (score each criterion 1 to 5; 2 and 4 are between the anchors)", ""]
    lines += [f"- **{c}**: {d}" for c, d in CRITERIA.items()]
    lines += ["", "## Answer schema", "```json", json.dumps(SCHEMA, indent=2), "```", ""]
    return "\n".join(lines)


def item_text(card, profile, verdict):
    beliefs = "\n".join(f"- [{b['id']}] {b['claim']}" for b in profile["beliefs"])
    shown = {k: verdict[k] for k in ("decision", "p_invest", "offer", "objections", "grill_question", "reasoning", "evidence")}
    return "\n".join([f"## Investor model: {profile['name']} (lens: {profile['lens']})", "", "Beliefs:", beliefs, "",
                      "## Pitch card", card_text(card), "", "## Verdict to grade", "```json",
                      json.dumps(shown, indent=2), "```"])


def prepare(args):
    src = RESULTS / f"llm_{args.shark}_{args.model}.jsonl"
    rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r.get("verdict")]
    rng = random.Random(11)
    # Over-sample INs: they are rare but carry the offer terms a buyer acts on.
    ins = [r for r in rows if r["verdict"]["decision"] == "in"]
    outs = [r for r in rows if r["verdict"]["decision"] != "in"]
    picked = ins[: args.n // 3] + rng.sample(outs, min(len(outs), args.n - min(len(ins), args.n // 3)))
    rng.shuffle(picked)
    profile = load(args.shark)
    cards = {r["pitch_id"]: r["card"] for r in load_jsonl(args.data)}
    items = [(r["pitch_id"], item_text(cards[r["pitch_id"]], profile, r["verdict"])) for r in picked]
    write_batches(job(args.shark), instructions(), items, args.batch_size)


def status(args):
    d = job(args.shark)
    batches = sorted(p.stem.split("-")[1] for p in d.glob("batch-*.md"))
    done = {p.stem.split("-")[1] for p in d.glob("out-*.jsonl")}
    print(f"{len(done)}/{len(batches)} batches have output. To do: {[b for b in batches if b not in done]}")


def collect(args):
    d = job(args.shark)
    key = json.loads((d / "key.json").read_text(encoding="utf-8"))
    answers, bad = read_answers(d)
    graded = []
    for item in key:
        a = answers.get(item)
        if a and all(isinstance(a.get(c), int) and 1 <= a[c] <= 5 for c in CRITERIA):
            graded.append(a)
    if not graded:
        raise SystemExit(f"No valid grades yet ({len(bad)} unparseable lines).")
    means = {c: sum(g[c] for g in graded) / len(graded) for c in CRITERIA}
    overall = sum(means.values()) / len(means)
    ok = all(m >= GATE_EACH for m in means.values()) and overall >= GATE_ALL
    out = [f"# Critique rubric: {args.shark} on {args.model}", "",
           f"**Verdict: {'PASS' if ok else 'FAIL'}** on {len(graded)} graded verdicts "
           f"({len(key) - len(graded)} missing or invalid).", "",
           "| criterion | mean (1-5) | bar |", "|---|---|---|"]
    out += [f"| {c} | {m:.2f} | >= {GATE_EACH} |" for c, m in means.items()]
    out += [f"| overall | {overall:.2f} | >= {GATE_ALL} |", "", "## Worst flaws (lowest-scored verdicts first)", ""]
    for g in sorted(graded, key=lambda g: sum(g[c] for c in CRITERIA))[:8]:
        out.append(f"- ({sum(g[c] for c in CRITERIA)}/25) {g.get('worst_flaw', '')}")
    out += ["", "Limit: the grader is the same model family as the judge. Read the flaws above yourself.", ""]
    report = "\n".join(out)
    path = RESULTS / f"rubric_{args.shark}_{args.model}.md"
    path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {path.relative_to(ROOT).as_posix()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["prepare", "status", "collect"])
    ap.add_argument("--shark", required=True)
    ap.add_argument("--model", default="claude-code")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--data", default=str(PROCESSED))
    args = ap.parse_args()
    {"prepare": prepare, "status": status, "collect": collect}[args.action](args)


if __name__ == "__main__":
    main()
