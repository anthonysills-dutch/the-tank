# Data handling and compliance

This document tells security, legal, and procurement teams what The Tank contains, what it does with data, and what it does not do. It uses ASD-STE100 Simplified Technical English.

## 1. What the product is

The product is a zip file of markdown files (`dist/the-tank-v<version>.zip`). It contains no code, no scripts, and no programs.

- The product cannot make a network connection.
- The product cannot collect telemetry or usage data.
- The product cannot send data to a person or to a server.

Your AI tool reads the files and does the work. The AI tool is the only part that runs.

## 2. Where your data goes

The Tank does not change how your AI tool handles data.

1. When you enter a pitch, your AI tool sends it to its model provider (for example, Anthropic for Claude).
2. The data terms of that provider apply. These terms include retention and model training.
3. Read the terms of your provider and your contract with it before you enter confidential pitch data.
4. The maker of The Tank receives no data from your sessions.
5. Session reports stay where your AI tool writes them.

## 3. What the Shark profiles contain

Each profile uses only the public record.

- The sources are published interviews, the investor's own writing, and news outlets. Each source has a URL in `sharks/<name>/profile.toml`.
- Each quote is word for word from its source and has 45 words or fewer.
- The profiles contain no private or confidential data.
- The models are simulations. They are not the real people, and they do not speak for them. See the notice in `README.md`.

The structure of a profile is in `sharks/profile.schema.json`. `tank/profiles.py` enforces it.

## 4. The source repository

This section is for the people who build the product. None of these files go into the zip file.

### 4.1 Network access

- The `tank/` library uses the Python standard library only. It makes no network calls.
- `scripts/fetch_wikipedia.py` and `scripts/fetch_sources.py` download public web pages. Only a maintainer runs them.
- Git ignores the downloaded source texts (`sharks/*/corpus/*.txt`) and the raw deal data (`data/raw/`).

### 4.2 Paid API scripts

`eval/run_llm.py`, `eval/probe_memorization.py`, and `eval/distinctiveness.py` call the Anthropic API.

- Each script shows a cost estimate first.
- Each script does not run without the `--yes` flag.
- Each script needs the Anthropic SDK and an API key. The rest of the repository needs neither.
- Do not use these scripts unless the owner approves the cost (README Section 4).

### 4.3 Anonymization of pitch cards

`tank/data.py` removes company names, founder names, websites, dates, and season numbers from each pitch card before a model sees it.

This control protects the backtest. It prevents a model from recognizing a televised pitch from memory. It is not a privacy control for your data.

### 4.4 Quote verification

1. `scripts/check_quotes.py --all` compares each quote with its downloaded source, word for word.
2. `scripts/build_package.py` stops if a quote fails.
3. `scripts/check_quotes.py <name> --verdict <file>` checks that each quote in a model verdict is a verified quote from the profile.

### 4.5 Automated checks

The tests use synthetic data. They need no network connection and no API key (README Section 5).

On each push and pull request to `main`, GitHub Actions (`.github/workflows/validate.yml`) does these checks:

1. It validates each Shark profile.
2. It checks the STE rules in `package_src/`.
3. It runs the tests.

The quote check needs the downloaded sources, and git ignores them. Thus, the quote check runs on the maintainer's computer before each build (README Section 2, step 3).
