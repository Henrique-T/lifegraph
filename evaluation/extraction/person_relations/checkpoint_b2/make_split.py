"""Create a deterministic development-only tuning/challenge split."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
RELATION_ROOT = HERE.parent
SEED = "LIFEGRAPH_RELATION_B2_SPLIT_V1_5448"
CORPORA = (
    RELATION_ROOT / "v1_adversarial.jsonl",
    RELATION_ROOT / "checkpoint_b_expansion.jsonl",
    RELATION_ROOT / "checkpoint_b1_generalization.jsonl",
)


def load_cases() -> list[dict]:
    """Load only approved development relation corpora."""
    return [json.loads(line) for path in CORPORA for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def bucket(case_id: str) -> int:
    """Return a stable 0--99 bucket independent of file ordering."""
    digest = hashlib.sha256(f"{SEED}|{case_id}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 100


def summary(cases: list[dict]) -> dict:
    """Describe relation and phenomenon representation in a split."""
    return {
        "narratives": len(cases),
        "candidates": sum(len(case["expected_relation_candidates"]) for case in cases),
        "relation_types": dict(sorted(Counter(
            candidate["relation_type"] for case in cases for candidate in case["expected_relation_candidates"]
        ).items())),
        "tags": dict(sorted(Counter(tag for case in cases for tag in case["tags"]).items())),
    }


def main() -> None:
    """Freeze a 70/30 hash split and its reproducibility metadata."""
    cases = load_cases()
    challenge = [case for case in cases if bucket(case["case_id"]) < 30]
    tuning = [case for case in cases if bucket(case["case_id"]) >= 30]
    for name, values in (("tuning_cases.json", tuning), ("challenge_cases.json", challenge)):
        (HERE / name).write_text(json.dumps(values, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    config = {
        "development_only": True,
        "seed": SEED,
        "algorithm": "SHA256(seed + '|' + case_id), first four bytes modulo 100; buckets 0-29 challenge",
        "corpus_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest().upper() for path in CORPORA},
        "tuning": summary(tuning),
        "challenge": summary(challenge),
        "split_hash": hashlib.sha256("|".join(case["case_id"] for case in challenge).encode()).hexdigest().upper(),
    }
    (HERE / "split_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
