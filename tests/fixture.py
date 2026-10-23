"""A synthetic CSV shaped like the Kaggle dataset. Fake companies, fake people, fake deals.

Cuban invests more often in pitches with revenue, so a working pipeline should let the
logistic baseline pick that up.
"""

import csv
import random

from tank.columns import SHARKS

INDUSTRIES = ["Food and Beverage", "Fashion/Beauty", "Lifestyle/Home", "Children/Education", "Fitness/Sports", "Technology"]


def write_fixture(path, n=240, seed=3):
    rng = random.Random(seed)
    headers = ["Season Number", "Episode Number", "Pitch Number", "Original Air Date", "Startup Name", "Industry",
               "Business Description", "Entrepreneur Names", "Company Website", "Multiple Entreprenuers",
               "Original Ask Amount", "Original Offered Equity", "Valuation Requested", "Got Deal",
               "Royalty Deal", "Loan", "Yearly Revenue", "Gross Margin"]
    for name in SHARKS.values():
        headers += [f"{name} Investment Amount", f"{name} Investment Equity", f"{name} Present"]

    rows = []
    for i in range(n):
        season = 1 + i * 8 // n
        company = f"Zorblax{i}"
        revenue = rng.choice([0, 0, 50_000, 250_000, 1_200_000])
        ask = rng.choice([50_000, 100_000, 250_000, 500_000])
        equity = rng.choice([5, 10, 15, 20, 25])
        row = {
            "Season Number": season, "Episode Number": 1 + i % 20, "Pitch Number": i + 1,
            "Original Air Date": f"20{10 + season:02d}-0{1 + i % 9}-1{i % 9}",
            "Startup Name": company, "Industry": rng.choice(INDUSTRIES),
            "Business Description": f"{company} makes a {rng.choice(['snack', 'gadget', 'toy', 'serum'])} invented by Quentin Varga. See {company.lower()}.com",
            "Entrepreneur Names": "Quentin Varga", "Company Website": f"https://www.{company.lower()}.com",
            "Multiple Entreprenuers": rng.choice(["0", "1"]),
            "Original Ask Amount": f"${ask:,}", "Original Offered Equity": f"{equity}%",
            "Valuation Requested": ask * 100 // equity, "Royalty Deal": "", "Loan": "",
            "Yearly Revenue": revenue or "", "Gross Margin": rng.choice(["", "40", "60"]),
        }
        p_cuban = 0.05 + (0.45 if revenue >= 250_000 else 0.0)
        any_deal = False
        for slug, name in SHARKS.items():
            present = slug != "john" or season > 1
            invests = present and rng.random() < (p_cuban if slug == "cuban" else 0.12)
            any_deal |= invests
            row[f"{name} Present"] = "1" if present else "0"
            row[f"{name} Investment Amount"] = ask if invests else ""
            row[f"{name} Investment Equity"] = equity + 10 if invests else ""
        row["Got Deal"] = "1" if any_deal else "0"
        rows.append(row)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
