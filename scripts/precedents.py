"""Print the pitch message (card + precedents) a Shark agent should receive. Used by the /tank skill.

    python scripts/precedents.py --shark cuban --pitch pitch.json
    python scripts/precedents.py --list
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tank import PROCESSED  # noqa: E402
from tank.data import load_jsonl  # noqa: E402
from tank.precedents import retrieve  # noqa: E402
from tank.profiles import sourced_slugs  # noqa: E402
from tank.prompt import pitch_message  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shark")
    ap.add_argument("--pitch", help="JSON file with card fields (see skills/tank/SKILL.md)")
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--list", action="store_true", help="Print the Sharks that have sourced profiles")
    args = ap.parse_args()

    if args.list:
        print(" ".join(sourced_slugs()))
        return
    card = json.loads(Path(args.pitch).read_text(encoding="utf-8"))
    pool = load_jsonl(PROCESSED) if PROCESSED.exists() else []
    print(pitch_message(card, retrieve(card, pool, args.shark, k=args.k)))


if __name__ == "__main__":
    main()
