# The Tank: Operations Manual

## 1. Purpose

The Tank lets you test a business pitch against six investor models before you pitch real investors. Each model finds the weak points that its investor finds most important.

The Tank does these things:

- It judges each pitch with six independent models.
- It gives each model's decision, offer terms, objections, and hardest question.
- It shows the past pitches that each investor heard, and the decisions.

The Tank does not do these things:

- It does not predict what a real investor will do.
- It does not give investment advice or legal advice.
- It does not speak for any real person.

## 2. Terms

| Term | Meaning |
|---|---|
| Shark model | One investor model. It is a simulation, not the real person. |
| Lens | The main thing that a Shark model judges, for example "sales". |
| Belief | One rule that a Shark model uses. Each belief has an ID. |
| Verified quote | A line that is word for word in a public source. Each has a source ID. |
| Past pitch | A pitch from the on-air record, with the name of the company removed. Each has an ID, for example `P-3fa2c1`. |
| Pitch card | The table of facts about your pitch. |
| Verdict | The result from one Shark model. |
| Session report | The full result: the pitch card, six verdicts, and a comparison. |
| Host | The AI that runs the session. The Host does not judge. |

## 3. Install

1. Give `INSTALLER.md` to your AI.
2. Do the steps that the AI gives you.
3. Make sure that the AI tells you "PASS" after the self-test.

If the self-test gives FAIL, see Section 9.

## 4. Run a pitch

1. Open a session with your AI in the installed folder or project.
2. Say "New pitch".
3. Describe the business. Include these facts:
   - What you sell, and to whom
   - The amount of money that you ask for
   - The percent of equity that you offer
   - Your sales in the last 12 months, or "pre-revenue"
4. Answer the questions of the AI. The AI asks one time only.
5. Wait for the session report.

NOTE: Give real numbers. If you do not give a number, the models treat it as "Not disclosed". A real investor also treats a missing number as a weakness.

## 5. Read the session report

1. Read the summary table first. It shows the decision of each model.
2. Read each verdict. The objections show what to fix before you pitch.
3. Read "The hardest question" in each verdict. Prepare an answer for each one.
4. Read "Where they split". These points depend on the lens of the investor.
5. Do the actions in "Next steps".

The probability of an offer starts from the real offer rate of that investor. Most pitches get OUT. A probability of 0.35 is a strong result for most Shark models.

## 6. Commands

| Say | Result |
|---|---|
| "New pitch" | A full session with all six Shark models |
| "Ask Cuban" (or another name) | A session with one Shark model |
| "Show the Sharks" | The name and lens of each Shark model |
| "Help" | The list of commands |

## 7. Sessions

If your AI can write files, it saves each session in `workspace/sessions/`. Each session folder has the pitch card and the report.

If your AI cannot write files, copy the report and keep it.

## 8. Limits

Read these limits before you use a result.

1. The models are simulations. A real investor can decide differently.
2. The on-air deal record contains only TV decisions. Some on-air deals changed or stopped after the show.
3. No open data source contains the sales figures that founders said on air. The past pitches show the product, the ask, the equity, and the decision only.
4. Product descriptions are long only for Seasons 1 to 8. Past pitches from later seasons have short descriptions.
5. Some models have few sources. Each Shark file has a section "Where this lens misfires". Read it.
6. On a chat assistant with no files (installer Type C), the models have no past-pitch library. The results are less accurate.

## 9. Troubleshooting

| Problem | Cause | Action |
|---|---|---|
| The AI does not know The Tank | The start file or project instructions are missing | Give `INSTALLER.md` to the AI again |
| The AI says that a file is missing | A file was not copied or uploaded | Do the installer again. For Type B, upload all 7 files from `upload-pack/`. |
| The self-test gives FAIL | The AI did not obey a procedure | Tell the AI the failed check number. Tell the AI to do the self-test again. |
| A verdict says "Mark Cuban says" | The AI did not obey Rule 2 | Tell the AI: "Obey Rule 2 in START-HERE.md." |
| A quote is not in the quote bank | The AI invented a quote | Tell the AI: "Remove each quote that is not in checks/quote-bank.md." |
| All six verdicts are the same | The AI did not judge independently | Tell the AI to use Method B in `procedures/run-a-pitch.md` |
| The AI looks up the company on the web | The AI did not obey Rule 6 | Tell the AI to stop. Start a new session. |

## 10. Data and licenses

See `LICENSES.md`. The deal records come from open datasets (CC0) and from Wikipedia (CC BY-SA 4.0). The past-pitch library is released under CC BY-SA 4.0.
