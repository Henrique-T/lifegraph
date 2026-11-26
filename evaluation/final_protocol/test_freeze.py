"""Test freeze."""

import hashlib
import json
from collections import Counter
from pathlib import Path

from schema import validate_dataset

HERE = Path(__file__).parent


def digest(path):
    """Calculate the SHA-256 digest of a fixture file."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_frozen_dataset_matches_schema_manifest_and_quotas():
    """Verify frozen dataset matches schema manifest and quotas."""
    dataset_path = HERE / "heldout_v1.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "dataset_manifest.json").read_text(encoding="utf-8"))
    validate_dataset(dataset)
    assert digest(dataset_path) == manifest["sha256"]
    assert len(dataset["narratives"]) == manifest["narrative_count"] == 100
    assert sum(len(row["expected_events"]) for row in dataset["narratives"]) == manifest["expected_event_count"] == 110
    assert Counter(category for row in dataset["narratives"] for category in row["categories"]) == Counter(manifest["category_counts"])


def test_frozen_protocol_and_prompt_hashes():
    """Verify frozen protocol and prompt hashes."""
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    recorded_protocol_hash = (HERE / "protocol.sha256").read_text(encoding="ascii").split()[0]
    assert digest(HERE / "protocol.json") == recorded_protocol_hash
    assert digest(HERE / "gemma_prompt.txt") == protocol["systems"]["C"]["prompt_sha256"]
    assert protocol["final_evaluation_protocol_frozen"] is True
    assert protocol["data"]["human_ground_truth_review"] is True
    review_path = HERE.parent.parent / Path(protocol["data"]["human_review_record"])
    assert digest(review_path) == protocol["data"]["human_review_sha256"]
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["dataset_sha256"] == protocol["data"]["held_out_sha256"]
    assert review["narratives_reviewed"] == 100
    assert review["expected_events_reviewed"] == 110
    assert review["decision"] == "APPROVED_WITHOUT_CORRECTIONS"
    assert protocol["final_model_comparison_authorized"] is True
