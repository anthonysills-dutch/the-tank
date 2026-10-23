---
name: tank
description: Put a business idea or pitch in front of investor models built from each original Shark's public record. Each Shark judges it separately (in/out, offer terms, top objections, the question they'd grill you on). Use when someone says "pitch this to the Sharks", "/tank", "would the Sharks invest", or wants an idea picked apart from several investor lenses.
---

# The Tank

Each Shark is an independent agent. They never see each other's verdicts. That separation is the product; do not merge, average or summarize their views into one.

The plugin root is two directories above this skill's base directory. Call it `ROOT` below.

## 1. Get the pitch facts

These investors judge on numbers. Collect what you can from the user's message, then ask once, in a single message, for anything missing from the **must have** list:

- **Must have:** what it is, the ask ($), equity offered (%), trailing 12-month sales ($, or "pre-revenue")
- **Should have:** gross margin (%), customers or traction, founder background, use of funds, industry

Do not invent numbers. If the user won't give one, leave it out: the card marks it "Not disclosed", and the Sharks treat that the way they would in the room.

Write the card to a temp file as JSON with these keys (omit unknowns):
`industry, description, ask_amount, ask_equity_pct, implied_valuation, team, yearly_revenue, monthly_revenue, gross_margin, net_margin, customers, founder_background, use_of_funds, other`.
Compute `implied_valuation` as `ask_amount / (ask_equity_pct / 100)`. Numbers are plain numbers (no `$` or `%`).

## 2. Find which Sharks are live

```bash
python "ROOT/scripts/precedents.py" --list
```

Only Sharks with sourced profiles print. Others are stubs: say in one line that they are not modeled yet. Never role-play a stub Shark yourself.

## 3. Build each Shark's brief

For each live Shark:

```bash
python "ROOT/scripts/precedents.py" --shark <slug> --pitch <card.json>
```

The output is the pitch card plus similar past pitches that Shark heard and what they did. If `data/processed/pitches.jsonl` is missing, it prints the card with no precedents; tell the user the deal history isn't loaded (see the README).

## 4. Run the Sharks separately, in parallel

Spawn one subagent per live Shark in a single message, with `subagent_type` `the-tank:shark-<slug>`. Each gets only its own brief from step 3, verbatim, and nothing about the other Sharks. Each returns a JSON verdict.

If that agent type isn't registered (agent files load when a session starts, so a fresh install or a newly sourced Shark may not be there yet), use `general-purpose` and start its prompt with: "Read ROOT/agents/shark-<slug>.md and follow it as your instructions for this whole task. Only read that file. Do not use web tools." Then the brief, verbatim.

## 4b. Check the quotes

Save each verdict to a temp file and run:

```bash
python "ROOT/scripts/check_quotes.py" <slug> --verdict <verdict file>
```

Anything a Shark put in quotation marks must be one of its verified quotes. If a quote fails, drop it from the report and say a quote was removed because it couldn't be verified. Never present an unverified line as something the real person said.

## 5. Report

For each Shark, in the order they were run:

- **Verdict:** IN or OUT, with the offer terms if IN
- **Top objections:** the three, as given
- **The question they'd grill you on**
- **Why:** the reasoning, in two or three sentences
- **Grounded in:** the belief ids and precedent ids from `evidence`

Then add a short **Where they agree / where they split** section. Comparing them is fine; blending them into a consensus verdict is not.

End with this line exactly:

> Simulated investor models built from public interviews and on-air deal records. Not affiliated with, endorsed by, or speaking for any real person or the show.

## Rules

- Never say "Mark Cuban says" or similar. Say "the Cuban model".
- Don't soften a Shark's verdict, and don't pile on extra criticism of your own.
- If a subagent returns malformed JSON, show what it returned and say it failed. Don't fill in a verdict yourself.
