# Procedure: Run a Pitch

Use this procedure when the user says "New pitch" or "Ask <Shark name>".

## 1. Collect the pitch

1. Do `procedures/intake.md`.
2. Make sure that the pitch card is complete before you continue.

## 2. Select the Sharks

1. For "New pitch", select all six Sharks.
2. For "Ask <Shark name>", select only that Shark.

## 3. Judge the pitch

The six judgments must be independent. Use method A if your platform can run sub-agents. Use method B if it cannot.

### Method A: sub-agents

1. Start one sub-agent for each selected Shark.
2. Give each sub-agent only these items:
   - Section 3 (Rules) of `START-HERE.md`
   - `procedures/judge-as-a-shark.md`
   - The file `sharks/<name>.md` for that Shark
   - The file `precedents/<name>.md` for that Shark
   - The pitch card
3. Do not give a sub-agent the verdict of a different Shark.
4. Collect each verdict.

### Method B: one Shark at a time

1. Judge the Sharks in this order: Cuban, O'Leary, Corcoran, Greiner, Herjavec, John.
2. For each Shark, do `procedures/judge-as-a-shark.md`.
3. Write the full verdict before you open the file of the next Shark.
4. Do not change a verdict after you write it.
5. Do not read a written verdict again until all verdicts are complete.

## 4. Check the quotes

1. Find each quoted line in each verdict.
2. Find the line in `checks/quote-bank.md`.
3. If the line is not in the quote bank, remove the line from the verdict.
4. If you remove a line, add this note to the verdict: "One quote was removed because it is not verified."

## 5. Write the report

1. Do `procedures/report.md`.
2. Show the report to the user.

## 6. Save the session

1. If your platform can write files, save the session in `workspace/sessions/<YYYY-MM-DD>-<short-name>/`.
2. Save the pitch card as `pitch-card.md`.
3. Save the report as `report.md`.
4. If your platform cannot write files, tell the user to copy the report and keep it.
