"""Audit relation-development corpora without accessing frozen evaluation data."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPORA = (
    ROOT / "v1_adversarial.jsonl",
    ROOT / "checkpoint_b_expansion.jsonl",
)
MOJIBAKE_MARKERS = ("Ã£", "Ã©", "Ã§", "Ã´", "Ã¡", "Ã­", "Ã³", "Ãº", "Ãª", "Ã")


def recursively_count(value: object, needle: str) -> int:
    """Count a literal sequence in every string of a decoded JSON object."""
    if isinstance(value, str):
        return value.count(needle)
    if isinstance(value, list):
        return sum(recursively_count(item, needle) for item in value)
    if isinstance(value, dict):
        return sum(recursively_count(item, needle) for item in value.values())
    return 0


def audit(path: Path) -> dict:
    """Return byte, UTF-8, and decoded-content integrity findings."""
    raw = path.read_bytes()
    decoded = raw.decode("utf-8", errors="strict")
    cases = [json.loads(line) for line in decoded.splitlines() if line.strip()]
    marker_counts = Counter()
    affected: dict[str, set[str]] = {}
    replacement_ids: list[str] = []
    for case in cases:
        case_id = case["case_id"]
        for marker in MOJIBAKE_MARKERS:
            count = recursively_count(case, marker)
            if count:
                marker_counts[marker] += count
                affected.setdefault(case_id, set()).add(marker)
        if recursively_count(case, "\ufffd"):
            replacement_ids.append(case_id)
    return {
        "file": path.name,
        "sha256_note": "Recorded separately by Git/checkpoint workflow",
        "byte_count": len(raw),
        "strict_utf8": True,
        "case_count": len(cases),
        "literal_u_fffd_count": decoded.count("\ufffd"),
        "literal_u_fffd_case_ids": replacement_ids,
        "mojibake_marker_counts": dict(marker_counts),
        "mojibake_case_ids": sorted(affected),
        "classification": (
            "VALID_UTF8_WITH_LITERAL_MOJIBAKE_AND_REPLACEMENT_DATA"
            if affected or replacement_ids
            else "VALID_UTF8_CLEAN"
        ),
    }


def main() -> None:
    """Write the machine-readable audit beside this script."""
    result = {"files": [audit(path) for path in CORPORA]}
    target = Path(__file__).with_name("encoding_findings.json")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
