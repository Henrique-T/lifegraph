"""Oracle tests for the development-only person-relation V1 corpus."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


CORPUS = Path(__file__).with_name("v1_adversarial.jsonl")
RELATION_TYPES = {
    "FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF",
    "BROTHER_OF", "SISTER_OF", "SPOUSE_OF",
}
POLARITIES = {"POSITIVE", "NEGATED"}
EPISTEMIC_STATUSES = {"ASSERTED", "UNCERTAIN", "HYPOTHETICAL"}
REPORTING_MODES = {"DIRECT", "REPORTED"}
TEMPORAL_SCOPES = {"CURRENT_OR_UNSPECIFIED", "PAST", "UNRESOLVED"}
REQUIRED_CANDIDATE_FIELDS = {
    "relation_type", "relation_surface_text", "endpoint_a_mention",
    "endpoint_b_mention", "polarity", "epistemic_status", "reporting_mode",
    "temporal_scope", "persistible_in_v1", "rationale",
}

BINDING_FIXTURES = (
    {"endpoint_a_person_id": "person-a", "endpoint_b_person_id": "person-b", "persistible": True},
    {"endpoint_a_person_id": "person-a", "endpoint_b_person_id": "person-a", "persistible": False},
    {"endpoint_a_person_id": "person-a", "endpoint_b_person_id": None, "persistible": False},
)

INDEPENDENT_CLAIM_FIXTURES = (
    {"claim_id": "claim-a", "turn_id": "turn-a", "canonical_pair_key": "PARENT:person-joao:person-maria"},
    {"claim_id": "claim-b", "turn_id": "turn-b", "canonical_pair_key": "PARENT:person-joao:person-maria"},
)

SIBLING_GROUP_FIXTURES = (
    {"relation_type": "BROTHER_OF", "endpoint_a": "person-joao", "endpoint_b": "person-maria", "canonical_pair_key": "SIBLING:person-joao:person-maria"},
    {"relation_type": "SISTER_OF", "endpoint_a": "person-maria", "endpoint_b": "person-joao", "canonical_pair_key": "SIBLING:person-joao:person-maria"},
)

CORRECTION_FIXTURES = (
    {"name": "valid_relation", "source": "João é pai de Maria.", "start": 7, "end": 13, "value": "pai de", "valid": True},
    {"name": "valid_endpoint", "source": "João é pai de Maria.", "start": 14, "end": 19, "value": "Maria", "valid": True},
    {"name": "invented_free_text", "source": "João é pai de Maria.", "start": 7, "end": 13, "value": "genitor", "valid": False},
    {"name": "out_of_range", "source": "João é pai de Maria.", "start": 14, "end": 99, "value": "Maria", "valid": False},
)


def load_cases() -> list[dict]:
    """Load independent JSON objects without accessing final-protocol artifacts."""
    return [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines() if line.strip()]


def candidates(cases: list[dict]):
    """Yield each case together with each expected candidate."""
    for case in cases:
        for candidate in case["expected_relation_candidates"]:
            yield case, candidate


def grounded_span(source: str, start: int, end: int, value: str) -> bool:
    """Apply the approved exact-offset correction rule."""
    return 0 <= start < end <= len(source) and source[start:end] == value


def binding_is_eligible(endpoint_a_person_id: str | None, endpoint_b_person_id: str | None) -> bool:
    """Apply the approved dual-existing-distinct-person binding predicate."""
    return bool(
        endpoint_a_person_id
        and endpoint_b_person_id
        and endpoint_a_person_id != endpoint_b_person_id
    )


def test_corpus_size_identity_and_structure() -> None:
    """Freeze the intended development-corpus size and basic shape."""
    cases = load_cases()
    assert len(cases) == 124
    assert len({case["case_id"] for case in cases}) == 124
    assert [case["case_id"] for case in cases] == [f"PR-{index:03d}" for index in range(1, 125)]
    assert all(set(case) == {"case_id", "narrative", "expected_relation_candidates", "tags"} for case in cases)
    assert all(case["narrative"].strip() and case["tags"] for case in cases)


def test_candidate_domains_and_balanced_vocabulary() -> None:
    """Require closed compositional domains and balanced relation coverage."""
    rows = list(candidates(load_cases()))
    assert len(rows) == 109
    assert all(set(candidate) == REQUIRED_CANDIDATE_FIELDS for _, candidate in rows)
    assert all(candidate["relation_type"] in RELATION_TYPES for _, candidate in rows)
    assert all(candidate["polarity"] in POLARITIES for _, candidate in rows)
    assert all(candidate["epistemic_status"] in EPISTEMIC_STATUSES for _, candidate in rows)
    assert all(candidate["reporting_mode"] in REPORTING_MODES for _, candidate in rows)
    assert all(candidate["temporal_scope"] in TEMPORAL_SCOPES for _, candidate in rows)
    assert Counter(candidate["relation_type"] for _, candidate in rows) == Counter({
        "FATHER_OF": 16, "MOTHER_OF": 15, "SON_OF": 15, "DAUGHTER_OF": 15,
        "BROTHER_OF": 16, "SISTER_OF": 16, "SPOUSE_OF": 16,
    })


def test_persistence_eligibility_is_conservative() -> None:
    """Ensure only direct, positive, asserted, complete, non-past candidates qualify."""
    rows = list(candidates(load_cases()))
    persistible = [(case, candidate) for case, candidate in rows if candidate["persistible_in_v1"]]
    assert len(persistible) == 45
    for case, candidate in rows:
        allowed = (
            candidate["polarity"] == "POSITIVE"
            and candidate["epistemic_status"] == "ASSERTED"
            and candidate["reporting_mode"] == "DIRECT"
            and candidate["temporal_scope"] == "CURRENT_OR_UNSPECIFIED"
            and candidate["endpoint_a_mention"] is not None
            and candidate["endpoint_b_mention"] is not None
        )
        assert candidate["persistible_in_v1"] is allowed, case["case_id"]


def test_every_blocking_dimension_has_nonpersistible_examples() -> None:
    """Prevent polarity, uncertainty, hypothesis, reporting, and partial loss."""
    rows = list(candidates(load_cases()))
    blocked_groups = {
        "negated": [candidate for _, candidate in rows if candidate["polarity"] == "NEGATED"],
        "uncertain": [candidate for _, candidate in rows if candidate["epistemic_status"] == "UNCERTAIN"],
        "hypothetical": [candidate for _, candidate in rows if candidate["epistemic_status"] == "HYPOTHETICAL"],
        "reported": [candidate for _, candidate in rows if candidate["reporting_mode"] == "REPORTED"],
        "partial": [candidate for _, candidate in rows if None in (candidate["endpoint_a_mention"], candidate["endpoint_b_mention"])],
        "past": [candidate for _, candidate in rows if candidate["temporal_scope"] == "PAST"],
    }
    assert {name: len(group) for name, group in blocked_groups.items()} == {
        "negated": 7, "uncertain": 21, "hypothetical": 7,
        "reported": 14, "partial": 14, "past": 8,
    }
    assert all(not candidate["persistible_in_v1"] for group in blocked_groups.values() for candidate in group)


def test_surface_provenance_and_spouse_variants_are_preserved() -> None:
    """Require exact source wording, including all approved spouse surface families."""
    rows = list(candidates(load_cases()))
    for case, candidate in rows:
        assert candidate["relation_surface_text"].casefold() in case["narrative"].casefold(), case["case_id"]
    spouse_surfaces = {
        candidate["relation_surface_text"].casefold()
        for _, candidate in rows if candidate["relation_type"] == "SPOUSE_OF"
    }
    assert {"marido de", "esposa de", "cônjuge de"} <= spouse_surfaces


def test_no_fake_identity_ref_or_event_derived_relation() -> None:
    """Enforce linguistic-only endpoints and the V1 event/REF boundaries."""
    cases = load_cases()
    forbidden_endpoint_values = {"unknown", "desconhecido", "unresolved", "person(unknown)"}
    for _, candidate in candidates(cases):
        for endpoint in (candidate["endpoint_a_mention"], candidate["endpoint_b_mention"]):
            assert endpoint is None or endpoint.casefold() not in forbidden_endpoint_values
    assert all(
        not case["expected_relation_candidates"]
        for case in cases if "event_only" in case["tags"]
    )
    serialized = CORPUS.read_text(encoding="utf-8").casefold()
    assert "ref_event" not in serialized and "refevent" not in serialized
    assert "person_id" not in serialized


def test_negative_and_multirelation_counts_are_deterministic() -> None:
    """Freeze no-candidate and coordinated multi-candidate expectations."""
    cases = load_cases()
    no_relation = [case for case in cases if not case["expected_relation_candidates"]]
    multi = [case for case in cases if len(case["expected_relation_candidates"]) > 1]
    assert len(no_relation) == 22
    assert len(multi) == 7
    assert all(len(case["expected_relation_candidates"]) == 2 for case in multi)
    assert all("multiple_relations" in case["tags"] for case in multi)


def test_same_person_and_missing_bindings_are_not_persistible() -> None:
    """Encode the backend gate requiring two distinct existing Person bindings."""
    for fixture in BINDING_FIXTURES:
        actual = binding_is_eligible(
            fixture["endpoint_a_person_id"], fixture["endpoint_b_person_id"]
        )
        assert actual is fixture["persistible"]


def test_independent_claims_are_not_collapsed_by_canonical_pair() -> None:
    """Keep independent ConversationTurn provenance despite structural equivalence."""
    assert len({item["claim_id"] for item in INDEPENDENT_CLAIM_FIXTURES}) == 2
    assert len({item["turn_id"] for item in INDEPENDENT_CLAIM_FIXTURES}) == 2
    assert len({item["canonical_pair_key"] for item in INDEPENDENT_CLAIM_FIXTURES}) == 1


def test_brother_and_sister_share_group_without_type_collapse_or_inverse_generation() -> None:
    """Group the pair structurally while preserving two independently declared forms."""
    assert [item["relation_type"] for item in SIBLING_GROUP_FIXTURES] == ["BROTHER_OF", "SISTER_OF"]
    assert len({item["canonical_pair_key"] for item in SIBLING_GROUP_FIXTURES}) == 1
    assert SIBLING_GROUP_FIXTURES[0]["endpoint_a"] == SIBLING_GROUP_FIXTURES[1]["endpoint_b"]
    assert SIBLING_GROUP_FIXTURES[0]["endpoint_b"] == SIBLING_GROUP_FIXTURES[1]["endpoint_a"]
    assert len(SIBLING_GROUP_FIXTURES) == 2  # supplied declarations only; no generated reverse claims


def test_corrections_are_exact_substrings_of_immutable_source() -> None:
    """Reject invented text and invalid offsets while accepting grounded corrections."""
    for fixture in CORRECTION_FIXTURES:
        assert grounded_span(
            fixture["source"], fixture["start"], fixture["end"], fixture["value"]
        ) is fixture["valid"], fixture["name"]


def test_current_and_past_spouse_cases_have_distinct_temporal_eligibility() -> None:
    """Keep historical spouse candidates reviewable but non-persistible in V1."""
    by_id = {case["case_id"]: case for case in load_cases()}
    current = by_id["PR-085"]["expected_relation_candidates"][0]
    past_a = by_id["PR-096"]["expected_relation_candidates"][0]
    past_b = by_id["PR-124"]["expected_relation_candidates"][0]
    assert (current["temporal_scope"], current["persistible_in_v1"]) == ("CURRENT_OR_UNSPECIFIED", True)
    assert all((item["temporal_scope"], item["persistible_in_v1"]) == ("PAST", False) for item in (past_a, past_b))


def test_required_phenomena_are_represented() -> None:
    """Ensure the corpus spans every approved adversarial phenomenon family."""
    tags = {tag for case in load_cases() for tag in case["tags"]}
    required = {
        "direct", "named", "narrator", "possessive", "direction", "sibling",
        "spouse_surface", "negation", "uncertainty", "hypothetical",
        "reported_speech", "speaker_distractor", "question", "quoted_language",
        "incidental_kinship", "partial_endpoint", "multiple_relations",
        "multiple_people", "distractors", "pronoun", "ambiguous", "false_friend",
        "past_relation", "temporal_limitation", "coordination",
        "no_event_derived_relation", "no_relation",
        "structural_pair", "independent_declaration", "duplicate_semantics",
    }
    assert required <= tags
