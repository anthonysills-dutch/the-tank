---
name: tank-eval
description: Run the-tank's memorization probe and Shark backtests inside Claude Code, on the user's plan, with no Anthropic API key or API spend. Use when the user says "run the backtest", "score the Cuban model", "/tank-eval", or wants to know whether a Shark model beats the baselines.
argument-hint: "<shark> [--test-on 7-8] [--batch-size 15]"
---

# Evaluate a Shark model without the API

Everything runs through Claude Code subagents, so it uses the user's plan, not an API bill. It does use a real share of plan usage: about one subagent per 15 pitches. A backtest on Seasons 7–8 is about 15 subagents per Shark, plus about 15 for the probe. Say this once before starting, and ask before going past one Shark.

Never use `eval/run_llm.py`, `eval/probe_memorization.py --yes`, or anything else that calls the Anthropic API. Those are for users who choose to pay for API runs.

## Steps

Default window: `--test-on 7-8`. Those are the seasons with full product descriptions; see the README.

1. **Baselines (free, local):** `python eval/baselines.py --shark <slug> --test-on 7-8`
2. **Prepare:**
   - `python eval/claude_code.py prepare probe --test-on 7-8`
   - `python eval/claude_code.py prepare backtest --shark <slug> --test-on 7-8`
3. **Run the batches.** For each job folder (`eval/work/probe/`, `eval/work/backtest-<slug>/`), spawn one subagent per `batch-NN.md`, up to six in one message, in parallel. Use `subagent_type: tank-evaluator`. If that type isn't registered in this session (agent files load at session start), use `general-purpose` and start the prompt with: "Read .claude/agents/tank-evaluator.md and follow it as your instructions. Use only Read and Write. No web tools." The prompt names the two files:
   `Instructions: <abs path>/instructions.md  Batch: <abs path>/batch-NN.md`
   Never pass `key.json` or any pitch id to a subagent.
4. **Check progress:** `python eval/claude_code.py status backtest --shark <slug>` (or `status probe`). Re-run any batch with no output once.
5. **Collect:**
   - `python eval/claude_code.py collect probe`
   - `python eval/claude_code.py collect backtest --shark <slug>`
6. **Score:** `python eval/score.py --shark <slug> --model claude-code`. Report the verdict line, the table for "not recognized by the model", the calibration table, and the offer-terms line. Say plainly if it FAILED.
7. **Critique checks (free, local):** `python eval/critique_checks.py --shark <slug>`. Report the pass rate of each check.

## Other jobs (same batch method as step 3)

- **Consistency** (about 6 subagents per Shark):
  `python eval/claude_code.py prepare repeat --shark <slug> --test-on 7-8 --n 45`, run the batches in `eval/work/repeat-<slug>/`,
  `python eval/claude_code.py collect repeat --shark <slug>`, then `python eval/consistency.py --shark <slug>`.
- **Critique rubric** (about 3 subagents per Shark; needs a finished backtest):
  `python eval/rubric.py prepare --shark <slug> --n 30`, run the batches in `eval/work/grade-<slug>/`,
  `python eval/rubric.py collect --shark <slug>`. Read the "worst flaws" lines; do not report only the means.

## Rules

- Batches are shuffled and items carry opaque ids. Don't reveal seasons, episodes or company names to subagents.
- One subagent judging 15 pitches in a row is less isolated than one call per pitch. Note that limit when reporting.
- Run the probe and the backtest with the same model, so "recognized" means recognized by the model that judged.
