"""Core library for the-tank: data loading, profiles, prompts, precedents, metrics.

Standard library only. The Anthropic SDK is needed only by the eval scripts that call the model.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARKS_DIR = ROOT / "sharks"
DATA_DIR = ROOT / "data"
PROCESSED = DATA_DIR / "processed" / "pitches.jsonl"
