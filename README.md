# the-tank (source repository)

This repository makes **The Tank**. The Tank is a set of six investor models. Each model uses the public record of one original Shark Tank investor. Each model judges a business pitch independently.

The Tank is a stress test for a pitch. It shows the objections, the hardest question, and the likely terms from six sourced investor lenses. In Tank mode, the models compete for the deal, and the founder negotiates. The Tank does not predict what a real investor will do. Section 6 shows why.

The product is a zip file of folders and markdown files. It works with each AI that can read files. The buyer gives `INSTALLER.md` to an AI, and the AI installs and tests the system. This repository contains the data, the checks, and the builder that make the zip file.

The documents in this file and in `package_src/` use ASD-STE100 Simplified Technical English.

## 1. Contents

| Folder | Contents |
|---|---|
| `package_src/` | The hand-written product files: README, installer, operations manual, procedures, templates, self-test |
| `sharks/<name>/profile.toml` | The profile of each Shark: lens, beliefs, verified quotes, misfires, sources |
| `sharks/<name>/corpus/` | The fetched source texts. Git ignores the texts. Only short quotes go in the product. |
| `data/` | The deal data and its licenses (see `data/README.md`) |
| `tank/` | The Python library: data, anonymization, statistics, past pitches, quotes, metrics |
| `scripts/` | The tools: fetch data and sources, check quotes, build the package, check STE |
| `eval/` | The baselines, the memorization probe, the backtest, the scorer, and the critique, consistency, and rubric tests |
| `skills/`, `agents/`, `.claude-plugin/` | An optional Claude Code plugin version (`/tank`) |
| `dist/` | The built package and the zip file (git ignores this folder) |

## 2. Build the product

Python 3.11 or later is necessary. No other software is necessary.

1. Prepare the data:
   ```bash
   python scripts/fetch_wikipedia.py
   python scripts/prepare_data.py data/raw/shark_tank_us.csv
   ```
2. Fetch the sources of each Shark:
   ```bash
   python scripts/fetch_sources.py cuban
   ```
   Do this step for each Shark: cuban, oleary, corcoran, greiner, herjavec, john.
3. Check the quotes:
   ```bash
   python scripts/check_quotes.py --all
   ```
   Each quote must be word for word in its source. Do not continue if a quote fails.
4. Check the STE rules:
   ```bash
   python scripts/ste_check.py
   ```
5. Build the package:
   ```bash
   python scripts/build_package.py
   ```
   The builder stops if a profile or a quote fails. The result is `dist/the-tank/` and `dist/the-tank-v<version>.zip`.
6. Set the version in `package_src/VERSION` before you release a new zip file.

## 3. Add or change a Shark

1. Add each source to `[[sources]]` in `sharks/<name>/profile.toml`.
2. Fetch the sources (`scripts/fetch_sources.py`).
3. Write each belief with one or more quotes. Copy each quote from the fetched text, not from a search result.
4. Write at least one `[[misfires]]` item.
5. Do steps 3 to 5 of Section 2.

WARNING: Search summaries can contain quotes that do not exist. Two such quotes were found and removed during this build. Use only text from the fetched sources.

## 4. Test the models (no API cost)

The model tests run in Claude Code with sub-agents. They use the Claude plan of the user. They do not use the Anthropic API. See `.claude/skills/tank-eval/SKILL.md`.

| Test | What it measures | Command | Gate |
|---|---|---|---|
| Backtest | Does the model predict on-air offers better than simple rules? | `eval/score.py` | Better Brier score than the best baseline (95% CI), and better F1 than the logistic rule and "always in" |
| Calibration | Does the probability match the real offer rate? | `eval/score.py` | Shown as a table. A useful model has a rising real rate from bin 1 to bin 3. |
| Critique checks | Does each verdict cite real beliefs, quote only verified lines, and use only numbers from the pitch card? | `eval/critique_checks.py` | Each check passes on 95% of verdicts |
| Consistency | Does the same pitch get the same verdict twice? | `eval/consistency.py` | Decision agreement 90%, signal agreement 80%, mean change in probability 0.05 or less |
| Critique rubric | Are the objections specific, in the lens, and useful? | `eval/rubric.py` | Each criterion 3.5 or more, overall 4.0 or more (scale 1 to 5) |

The decision threshold is the offer rate of the Shark in the training seasons, not 0.5. Most Sharks invest in fewer than 20% of pitches, so a calibrated model almost never says 0.5.

The API scripts (`eval/run_llm.py`, `eval/probe_memorization.py --yes`) are optional. They cost money. Do not use them unless the owner approves the cost.

## 5. Run the tests

```bash
python -m unittest discover tests
```

The tests use synthetic data. They need no network connection and no API key.

## 6. Status

| Shark | Lens | Verified quotes | Sources |
|---|---|---|---|
| Cuban | Sales and the founder's grit | 31 | 12 (4 of his own blog posts) |
| O'Leary | Cash flow and royalty structures | 10 | 4 |
| Corcoran | The founder as a person | 13 | 4 |
| Greiner | Retail and TV-shopping fit | 6 | 3 |
| Herjavec | Scale and the founder's ability to sell | 9 | 4 |
| John | The founder's influence and fit with his portfolio | 10 | 3 |

### 6.1 Test results (Cuban model, holdout Seasons 7 and 8)

The other five Shark models have not had a full backtest yet.

| Test | Result | Details |
|---|---|---|
| Backtest | FAIL | 117 pitches that the model did not recognize, with 11 real offers. AUC 0.567. Brier 0.088 against 0.094 for the base rate, but the 95% CI includes zero. |
| Calibration | Weak | Mean probability 0.115 against a real offer rate of 0.094. The real rate does not rise from bin 2 to bin 3. |
| Critique checks | PASS | 211 verdicts. Evidence, quotes, structure, and offer terms: 100%. Numbers from the pitch card: 99.1%. |
| Consistency | Not run | The job is ready: `eval/work/repeat-cuban/` (6 batches). |
| Critique rubric | Not run | The job is ready: `eval/work/grade-cuban/` (3 batches). |

The model recognized 94 of 211 test pitches from memory. The backtest uses only the pitches that it did not recognize.

**What this means.** The Cuban model does not predict on-air decisions better than the base rate. The pitch cards do not contain the sales figures that the Sharks heard on air, and the test set has few offers. Thus, The Tank makes no accuracy claim. Its value is the critique: objections, questions, and terms from sourced investor lenses.

### 6.2 Tank mode

Tank mode is in the package (`package_src/system/procedures/tank-mode.md`) and in the plugin (`skills/tank/SKILL.md`, section 6). The Sharks hold, improve, partner, or drop their offers in two rounds. Then the founder accepts, counters, or walks away. The terms come from the negotiation record of each Shark. The record gives the median deal valuation compared with the ask. It also gives the share of deals at the full ask and the partners in shared deals. Tank mode has not had a recorded test session yet.

## 7. Known limits

1. No open data source contains the sales figures that founders said on air.
2. Long product descriptions exist only for Seasons 1 to 8. Use `--test-on 7-8` for the backtest.
3. The labels are on-air decisions. Some on-air deals changed after the show.
4. Greiner, Herjavec, and John have few sources. Their profiles say so in "Where this lens misfires".
5. The sources do not support a "brand and licensing" lens for John or a "margins" lens for Herjavec. The lenses follow the sources.
6. The model can recognize many televised pitches from memory. Each backtest reports only the pitches that the model did not recognize.
7. In the Claude Code tests, one sub-agent judges a batch of 15 pitches. This is less independent than one call for each pitch.
8. The rubric grader is the same model family as the judge. A rubric PASS is necessary, but it is not sufficient. Read the "worst flaws" list.

## 8. Notice

The models are simulations built from public records. They are not the real people and do not speak for them. They are not affiliated with, or endorsed by, any real person, ABC, or Sony Pictures Television. "Shark Tank" is a trademark of its owner.

## 9. Licenses

The code is MIT (`LICENSE`). The data licenses are in `data/README.md`.
