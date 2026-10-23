# Data

Deal facts only. No transcripts or video are used or committed.

## Sources

| Source | License | What we take | Coverage |
|---|---|---|---|
| [Shark Tank US dataset](https://www.kaggle.com/datasets/thirumani/shark-tank-us-dataset) (Satya Thirumani, Kaggle v34) | CC0 | Base records: ask, equity, valuation, industry, who invested and on what terms, panel presence | Seasons 1–17, 1,484 pitches |
| [All Shark Tank (US) Pitches & Deals](https://www.kaggle.com/datasets/neiljs/all-shark-tank-us-pitches-deals) (neiljs, Kaggle) | CC0 | Longer product descriptions | Seasons 1–8 |
| [Shark Tank Pitches](https://www.kaggle.com/datasets/rahulsathyajit/shark-tank-pitches) (rahulsathyajit, Kaggle) | CC0 | Product descriptions, founder names (used only to anonymize) | Seasons 1–6 |
| Wikipedia, "Shark Tank season 1" through "season 17" | CC BY-SA 4.0 | Who sat on the panel each episode, short product descriptors, YES/NO as a cross-check | Seasons 1–17 |

Kaggle licenses are the uploader's declaration. The neiljs descriptions read like marketing copy and may originally come from the companies or the network. We use them as short factual descriptors and never present them as our own writing.

**Wikipedia attribution.** Panel presence and some descriptors come from these revisions of the English Wikipedia "Shark Tank season N" articles (CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/): S1 1354672552, S2 1354672617, S3 1354672631, S4 1357297865, S5 1359045605, S6 1354672664, S7 1370894722, S8 1354672683, S9 1379635238, S10 1354672560, S11 1354672568, S12 1354672574, S13 1354672580, S14 1354672588, S15 1376538673, S16 1354672611, S17 1374395624. Because of share-alike, `data/processed/pitches.jsonl` is released under CC BY-SA 4.0. The code stays MIT.

## What the merge checks

`scripts/prepare_data.py` prints a report on every run. As of the current sources:

- **Panel presence:** Wikipedia filled 2,633 blank "Present" cells. Where both sources had a value, they agreed on 5,309 of 5,317 cells (99.8%). Explicit Kaggle values are never overwritten.
- **Deal labels:** Wikipedia's YES/NO matched Kaggle's deal flag on 722 of 723 pitches.
- **Descriptions:** 737 pitches got a longer description, almost all in Seasons 1–8. Seasons 9–17 still carry ~25-character descriptors.
- **Sales:** no openly licensed source has the revenue founders state on air. Cards say "Not disclosed".

Each record's `provenance` field says where its description and any filled presence came from.

## Rebuild

```bash
# Kaggle (anonymous download works for these public datasets)
curl -L -o shark.zip https://www.kaggle.com/api/v1/datasets/download/thirumani/shark-tank-us-dataset
# unzip into data/raw/shark_tank_us.csv; the two description CSVs go in data/raw/sources/
python scripts/fetch_wikipedia.py          # polite, resumable, backs off on 429
python scripts/prepare_data.py data/raw/shark_tank_us.csv
python scripts/build_agents.py
```

`prepare_data.py` also reports how many cards still contain the company name (it should be 0). If a dataset renames a column, add an alias in `tank/columns.py`.
