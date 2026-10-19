"""Development-only adversarial characterization of person-event association."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app.model import GLiNERModel
from app.subject_association import conservative_guards_association


@dataclass(frozen=True)
class ExpectedEvent:
    """Expected subject assignment for one supplied civil-event trigger."""

    event_type: str
    trigger: str
    subject_role: str
    subject_text: str | None


@dataclass(frozen=True)
class AdversarialCase:
    """Synthetic development case with explicit safety expectations."""

    case_id: str
    phenomenon: str
    narrative: str
    people: tuple[str, ...]
    dates: tuple[str, ...]
    expected_events: tuple[ExpectedEvent, ...]
    narrator_attribution_unsafe: bool
    rationale: str


CASES = (
    AdversarialCase(
        "ADV-01", "first_person", "Nasci em 1990.", (), ("1990",),
        (ExpectedEvent("nascimento", "Nasci", "NARRATOR", "__NARRATOR__"),),
        False, "The first-person verb form explicitly identifies the narrator.",
    ),
    AdversarialCase(
        "ADV-02", "first_person", "Em 2015 me casei.", (), ("2015",),
        (ExpectedEvent("casamento", "me casei", "NARRATOR", "__NARRATOR__"),),
        False, "The clitic and first-person verb explicitly identify the narrator.",
    ),
    AdversarialCase(
        "ADV-03", "first_person", "Morri em 2020.", (), ("2020",),
        (ExpectedEvent("obito", "Morri", "UNRESOLVED", None),),
        False, "First-person death is intentionally outside the current safe narrator rules.",
    ),
    AdversarialCase(
        "ADV-04", "explicit_third_party", "João nasceu em 1990.", ("João",), ("1990",),
        (ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "João"),),
        True, "The named person immediately precedes the event.",
    ),
    AdversarialCase(
        "ADV-05", "explicit_third_party", "Maria se casou em 2018.", ("Maria",), ("2018",),
        (ExpectedEvent("casamento", "se casou", "THIRD_PARTY", "Maria"),),
        True, "The named person is the explicit grammatical subject.",
    ),
    AdversarialCase(
        "ADV-06", "pro_drop_continuity", "Ana nasceu em 1990 e casou em 2015.", ("Ana",), ("1990", "2015"),
        (
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Ana"),
            ExpectedEvent("casamento", "casou", "THIRD_PARTY", "Ana"),
        ),
        True, "Same-sentence coordination safely carries the explicit subject.",
    ),
    AdversarialCase(
        "ADV-07", "pro_drop_ambiguous", "Casou em 2019.", (), ("2019",),
        (ExpectedEvent("casamento", "Casou", "UNRESOLVED", None),),
        True, "No linguistic evidence identifies narrator or third party.",
    ),
    AdversarialCase(
        "ADV-08", "narrator_and_third_party", "Nasci em 1988 e Maria se casou em 2019.", ("Maria",), ("1988", "2019"),
        (
            ExpectedEvent("nascimento", "Nasci", "NARRATOR", "__NARRATOR__"),
            ExpectedEvent("casamento", "se casou", "THIRD_PARTY", "Maria"),
        ),
        False, "The explicit third-party subject must override narrator continuity.",
    ),
    AdversarialCase(
        "ADV-09", "narrator_and_third_party", "Maria nasceu em 1990 e me casei em 2019.", ("Maria",), ("1990", "2019"),
        (
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Maria"),
            ExpectedEvent("casamento", "me casei", "NARRATOR", "__NARRATOR__"),
        ),
        False, "First-person evidence must replace third-party continuity.",
    ),
    AdversarialCase(
        "ADV-10", "reported_speech", "João disse que Maria se casou em 2018.", ("João", "Maria"), ("2018",),
        (ExpectedEvent("casamento", "se casou", "THIRD_PARTY", "Maria"),),
        True, "The reporting speaker is not the embedded event subject.",
    ),
    AdversarialCase(
        "ADV-11", "reported_speech", "João disse que se casou em 2018.", ("João",), ("2018",),
        (ExpectedEvent("casamento", "se casou", "UNRESOLVED", None),),
        True, "The current surface evidence does not safely resolve the embedded omission.",
    ),
    AdversarialCase(
        "ADV-12", "reported_speech_narrator", "Meu pai disse que casei em 2019.", ("pai",), ("2019",),
        (ExpectedEvent("casamento", "casei", "NARRATOR", "__NARRATOR__"),),
        False, "The embedded first-person verb refers to the narrative speaker, not the reporter.",
    ),
    AdversarialCase(
        "ADV-13", "kinship", "Minha mãe nasceu em 1960.", ("mãe",), ("1960",),
        (ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Minha mãe"),),
        True, "The kinship phrase explicitly names a third-party subject.",
    ),
    AdversarialCase(
        "ADV-14", "kinship", "Meu pai morreu em 2020 e minha filha nasceu em 2021.", ("pai", "filha"), ("2020", "2021"),
        (
            ExpectedEvent("obito", "morreu", "THIRD_PARTY", "Meu pai"),
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "minha filha"),
        ),
        True, "Each clause contains a distinct explicit kinship subject.",
    ),
    AdversarialCase(
        "ADV-15", "multiple_people", "João e Maria disseram que Ana nasceu em 2000.", ("João", "Maria", "Ana"), ("2000",),
        (ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Ana"),),
        True, "Only the person inside the reported clause is the event subject.",
    ),
    AdversarialCase(
        "ADV-16", "multiple_people", "João encontrou Pedro antes de Ana nascer em 2000.", ("João", "Pedro", "Ana"), ("2000",),
        (ExpectedEvent("nascimento", "nascer", "THIRD_PARTY", "Ana"),),
        True, "The person adjacent to the infinitive is its explicit subject.",
    ),
    AdversarialCase(
        "ADV-17", "coordinated_events", "Ana nasceu em 1990, casou em 2015 e morreu em 2024.", ("Ana",), ("1990", "2015", "2024"),
        (
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Ana"),
            ExpectedEvent("casamento", "casou", "THIRD_PARTY", "Ana"),
            ExpectedEvent("obito", "morreu", "THIRD_PARTY", "Ana"),
        ),
        True, "Comma and conjunction preserve one explicit subject in the sentence.",
    ),
    AdversarialCase(
        "ADV-18", "coordinated_events", "Ana nasceu em 1990 enquanto casou em 2015.", ("Ana",), ("1990", "2015"),
        (
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Ana"),
            ExpectedEvent("casamento", "casou", "THIRD_PARTY", "Ana"),
        ),
        True, "The subordinate connector retains the same overt subject.",
    ),
    AdversarialCase(
        "ADV-19", "repeated_event_type", "Ana se casou em 2001 e se casou novamente em 2010.", ("Ana",), ("2001", "2010"),
        (
            ExpectedEvent("casamento", "se casou", "THIRD_PARTY", "Ana"),
            ExpectedEvent("casamento", "se casou", "THIRD_PARTY", "Ana"),
        ),
        True, "Repeated event type must retain the established subject without merging events.",
    ),
    AdversarialCase(
        "ADV-20", "repeated_event_type", "Ana se casou em 2001, mas Beatriz se casou em 2010.", ("Ana", "Beatriz"), ("2001", "2010"),
        (
            ExpectedEvent("casamento", "se casou", "THIRD_PARTY", "Ana"),
            ExpectedEvent("casamento", "se casou", "THIRD_PARTY", "Beatriz"),
        ),
        True, "The explicit subject switch must override repeated-type continuity.",
    ),
    AdversarialCase(
        "ADV-21", "incidental_person", "Depois de falar com Ana, Maria morreu em 2020.", ("Ana", "Maria"), ("2020",),
        (ExpectedEvent("obito", "morreu", "THIRD_PARTY", "Maria"),),
        True, "The object of 'com' is incidental; Maria is the explicit subject.",
    ),
    AdversarialCase(
        "ADV-22", "incidental_person", "No casamento de Ana, João morreu em 2020.", ("Ana", "João"), ("2020",),
        (ExpectedEvent("obito", "morreu", "THIRD_PARTY", "João"),),
        True, "Ana occurs in background context while João is the explicit death subject.",
    ),
    AdversarialCase(
        "ADV-23", "subject_switch", "Maria nasceu em 1990, mas João morreu em 2020.", ("Maria", "João"), ("1990", "2020"),
        (
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Maria"),
            ExpectedEvent("obito", "morreu", "THIRD_PARTY", "João"),
        ),
        True, "An explicit person in the second clause replaces the prior subject.",
    ),
    AdversarialCase(
        "ADV-24", "ambiguous_pronoun", "João encontrou Pedro e ele se casou em 2019.", ("João", "Pedro"), ("2019",),
        (ExpectedEvent("casamento", "se casou", "UNRESOLVED", None),),
        True, "Two plausible antecedents make the pronoun unsafe to resolve.",
    ),
    AdversarialCase(
        "ADV-25", "pronoun_continuity", "Maria nasceu em 1990. Ela se casou em 2015.", ("Maria",), ("1990", "2015"),
        (
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Maria"),
            ExpectedEvent("casamento", "se casou", "UNRESOLVED", None),
        ),
        True, "Cross-sentence pronoun resolution is intentionally outside the current safe rules.",
    ),
    AdversarialCase(
        "ADV-26", "coordinated_subject", "Carlos e Beatriz se casaram em 2018.", ("Carlos", "Beatriz"), ("2018",),
        (ExpectedEvent("casamento", "se casaram", "UNRESOLVED", None),),
        True, "The single-subject schema cannot safely represent the plural subject.",
    ),
    AdversarialCase(
        "ADV-27", "false_narrator_trap", "João afirmou que casou em 2018.", ("João",), ("2018",),
        (ExpectedEvent("casamento", "casou", "UNRESOLVED", None),),
        True, "Missing embedded subject evidence must not default to narrator.",
    ),
    AdversarialCase(
        "ADV-28", "false_narrator_trap", "Sobre Maria, disseram que nasceu em 1990.", ("Maria",), ("1990",),
        (ExpectedEvent("nascimento", "nasceu", "UNRESOLVED", None),),
        True, "A topical mention does not safely establish the omitted embedded subject.",
    ),
    AdversarialCase(
        "ADV-29", "reported_speech", "João e Maria disseram que nasceu em 2000.", ("João", "Maria"), ("2000",),
        (ExpectedEvent("nascimento", "nasceu", "UNRESOLVED", None),),
        True, "A plural reporting verb does not supply a missing embedded subject.",
    ),
    AdversarialCase(
        "ADV-30", "multiple_people", "João encontrou Pedro antes de nascer em 2000.", ("João", "Pedro"), ("2000",),
        (ExpectedEvent("nascimento", "nascer", "UNRESOLVED", None),),
        True, "The infinitive has no explicit local subject after the clause boundary.",
    ),
    AdversarialCase(
        "ADV-31", "incidental_person", "No casamento de Ana, morreu em 2020.", ("Ana",), ("2020",),
        (ExpectedEvent("obito", "morreu", "UNRESOLVED", None),),
        True, "The contextual person before the comma is not the omitted death subject.",
    ),
    AdversarialCase(
        "ADV-32", "coordinated_events", "Ana nasceu em 1990 enquanto Beatriz casou em 2015.", ("Ana", "Beatriz"), ("1990", "2015"),
        (
            ExpectedEvent("nascimento", "nasceu", "THIRD_PARTY", "Ana"),
            ExpectedEvent("casamento", "casou", "THIRD_PARTY", "Beatriz"),
        ),
        True, "An explicit subject after 'enquanto' overrides subject continuity.",
    ),
    AdversarialCase(
        "ADV-33", "coordinated_events", "Ana e Beatriz nasceram em 1990 enquanto casou em 2015.", ("Ana", "Beatriz"), ("1990", "2015"),
        (
            ExpectedEvent("nascimento", "nasceram", "UNRESOLVED", None),
            ExpectedEvent("casamento", "casou", "UNRESOLVED", None),
        ),
        True, "An unresolved plural subject cannot be propagated through 'enquanto'.",
    ),
)


def _span(text: str, value: str, after: int = 0) -> dict:
    """Create an exact synthetic span from independently authored text."""
    start = text.index(value, after)
    return {"text": value, "start": start, "end": start + len(value)}


def evaluate_case(case: AdversarialCase) -> list[dict]:
    """Run one case through the unchanged conservative association function."""
    triggers = []
    cursor = 0
    for expected in case.expected_events:
        item = _span(case.narrative, expected.trigger, cursor)
        triggers.append({
            **item,
            "event_type": expected.event_type,
            "trigger_text": expected.trigger,
            "trigger_start": item["start"],
            "trigger_end": item["end"],
        })
        cursor = item["end"]
    people = [_span(case.narrative, value) for value in case.people]
    dates = [_span(case.narrative, value) for value in case.dates]
    return conservative_guards_association(case.narrative, triggers, people, dates)


def subject_role(result: dict) -> str:
    """Map an association result to the protocol's normalized subject role."""
    if result["subject_resolution"] == "UNRESOLVED":
        return "UNRESOLVED"
    if result["subject_text"] == "__NARRATOR__":
        return "NARRATOR"
    return "THIRD_PARTY"


def classify_event(expected: ExpectedEvent, actual: dict) -> str:
    """Classify one observed event without treating abstention as failure by default."""
    actual_role = subject_role(actual)
    if actual["event_type"] != expected.event_type:
        return "FAIL_EVENT_EXTRACTION"
    if actual_role == expected.subject_role and actual.get("subject_text") == expected.subject_text:
        return "PASS_SAFE_ABSTENTION" if actual_role == "UNRESOLVED" else "PASS_SAFE_RESOLUTION"
    if actual_role == "NARRATOR" and expected.subject_role != "NARRATOR":
        return "FAIL_FALSE_NARRATOR_ATTRIBUTION"
    if actual_role != "UNRESOLVED":
        return "FAIL_WRONG_RESOLVED_SUBJECT"
    return "FAIL_OTHER"


class FakeStage1Extractor:
    """Return fixed Stage-1 spans while exercising the production boundary."""

    def __init__(self, entities: dict[str, list[dict]]) -> None:
        self.entities = entities

    def extract_entities(self, *_args, **_kwargs) -> dict:
        """Return deterministic entity spans without invoking a model."""
        return {"entities": self.entities}


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.case_id)
def test_current_person_event_association(case: AdversarialCase) -> None:
    """Compare current output with the independently defined safety expectation."""
    actual = evaluate_case(case)
    assert len(actual) == len(case.expected_events)
    observations = [
        classify_event(expected, observed)
        for expected, observed in zip(case.expected_events, actual, strict=True)
    ]
    assert all(value.startswith("PASS_") for value in observations), observations


def test_production_boundary_keeps_narrator_and_third_party_separate() -> None:
    """Exercise production mapping with a mixed narrator/third-party fixture."""
    case = next(item for item in CASES if item.case_id == "ADV-08")
    service = GLiNERModel()
    service._model = FakeStage1Extractor({
        "birth_expression": [{**_span(case.narrative, "Nasci"), "confidence": 1.0}],
        "marriage_expression": [{**_span(case.narrative, "se casou"), "confidence": 1.0}],
        "person": [{**_span(case.narrative, "Maria"), "confidence": 1.0}],
        "date": [
            {**_span(case.narrative, "1988"), "confidence": 1.0},
            {**_span(case.narrative, "2019"), "confidence": 1.0},
        ],
    })

    result = asyncio.run(service.extract(case.narrative))

    assert [item.subject_text for item in result.candidates] == ["__NARRATOR__", "Maria"]


def test_production_boundary_preserves_safe_reported_speech_abstention() -> None:
    """Exercise production mapping for unresolved reported speech."""
    case = next(item for item in CASES if item.case_id == "ADV-11")
    service = GLiNERModel()
    service._model = FakeStage1Extractor({
        "marriage_expression": [{**_span(case.narrative, "se casou"), "confidence": 1.0}],
        "person": [{**_span(case.narrative, "João"), "confidence": 1.0}],
        "date": [{**_span(case.narrative, "2018"), "confidence": 1.0}],
    })

    result = asyncio.run(service.extract(case.narrative))

    assert result.candidates[0].subject_resolution == "UNRESOLVED"
    assert result.candidates[0].subject_text is None
