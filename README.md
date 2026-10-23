# the-tank (source repository)

This repository makes **The Tank**. The Tank is a set of six investor models. Each model uses the public record of one original Shark Tank investor. Each model judges a business pitch independently.

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
| `eval/` | The baselines, the memorization probe, the backtest, and the scorer |
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

The backtest runs in Claude Code with sub-agents. It uses the Claude plan of the user. It does not use the Anthropic API. See `.claude/skills/tank-eval/SKILL.md`.

1. Run the baselines: `python eval/baselines.py --shark cuban --test-on 7-8`
2. Do the steps in the `tank-eval` skill.
3. Score: `python eval/score.py --shark cuban --model claude-code`

A model passes only if it is better than all baselines on pitches that the model does not recognize. The API scripts (`eval/run_llm.py`, `eval/probe_memorization.py --yes`) are optional. They cost money. Do not use them unless the owner approves the cost.

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

The backtest has not run yet. Tank mode (Sharks that bid against each other) is planned as a later layer.

## 7. Known limits

1. No open data source contains the sales figures that founders said on air.
2. Long product descriptions exist only for Seasons 1 to 8. Use `--test-on 7-8` for the backtest.
3. The labels are on-air decisions. Some on-air deals changed after the show.
4. Greiner, Herjavec, and John have few sources. Their profiles say so in "Where this lens misfires".
5. The sources do not support a "brand and licensing" lens for John or a "margins" lens for Herjavec. The lenses follow the sources.

## 8. Notice

The models are simulations built from public records. They are not the real people and do not speak for them. They are not affiliated with, or endorsed by, any real person, ABC, or Sony Pictures Television. "Shark Tank" is a trademark of its owner.

## 9. Licenses

The code is MIT (`LICENSE`). The data licenses are in `data/README.md`.
