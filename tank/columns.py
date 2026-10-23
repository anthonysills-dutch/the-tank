"""Maps the raw Kaggle CSV headers to canonical field names.

The source is "Shark Tank US dataset" by Satya Thirumani on Kaggle (CC0). Its headers have
changed between versions, so matching ignores case and punctuation, and each field accepts
aliases. Required fields fail loudly; optional ones (revenue, margins) are used only if present.
"""

import re

# The original six. Guest Sharks are deliberately out of scope.
SHARKS = {
    "cuban": "Mark Cuban",
    "oleary": "Kevin O'Leary",
    "corcoran": "Barbara Corcoran",
    "greiner": "Lori Greiner",
    "herjavec": "Robert Herjavec",
    "john": "Daymond John",
}

REQUIRED = {
    "season": ["Season Number", "Season"],
    "episode": ["Episode Number", "Episode"],
    "industry": ["Industry"],
    "description": ["Business Description", "Description"],
    "name": ["Startup Name", "Company", "Business Name"],
    "ask_amount": ["Original Ask Amount", "Ask Amount"],
    "ask_equity": ["Original Offered Equity", "Offered Equity"],
    "got_deal": ["Got Deal", "Deal"],
}

OPTIONAL = {
    "pitch": ["Pitch Number"],
    "air_date": ["Original Air Date", "Air Date"],
    "valuation": ["Valuation Requested"],
    "entrepreneurs": ["Entrepreneur Names", "Entrepreneurs"],
    "website": ["Company Website", "Website"],
    "multiple_founders": ["Multiple Entreprenuers", "Multiple Entrepreneurs"],
    "royalty": ["Royalty Deal"],
    "loan": ["Loan"],
    # Financials. When present these matter more than anything else on the card.
    "yearly_revenue": ["Yearly Revenue"],
    "monthly_revenue": ["Monthly Revenue"],
    "gross_margin": ["Gross Margin"],
    "net_margin": ["Net Margin"],
    "has_patents": ["Has Patents"],
    "bootstrapped": ["Bootstrapped"],
}


def shark_fields(slug):
    name = SHARKS[slug]
    return {
        f"{slug}_amount": [f"{name} Investment Amount"],
        f"{slug}_equity": [f"{name} Investment Equity"],
        f"{slug}_present": [f"{name} Present"],
    }


def norm(header):
    return re.sub(r"[^a-z0-9]", "", header.lower())


def resolve(headers):
    """Return {canonical: actual_header} and a list of missing required fields."""
    by_norm = {norm(h): h for h in headers}
    wanted = dict(REQUIRED)
    wanted.update(OPTIONAL)
    for slug in SHARKS:
        wanted.update(shark_fields(slug))

    found, missing = {}, []
    for field, aliases in wanted.items():
        hit = next((by_norm[norm(a)] for a in aliases if norm(a) in by_norm), None)
        if hit:
            found[field] = hit
        elif field in REQUIRED:
            missing.append(field)
    return found, missing
