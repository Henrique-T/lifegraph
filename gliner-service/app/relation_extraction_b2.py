"""Checkpoint B.2 structural Person-Relation extraction experiments.

The module is intentionally unreachable from application routes.  It separates
detector evidence from family-level structural interpretation and safety guards.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from app.model import MODEL_ID, MODEL_REVISION
from app.relation_schemas import RelationCandidate, RelationDetection, RelationExtractionResult


PIPELINE_ID = "LIFEGRAPH_PERSON_RELATION_V1"
A0_B2_MODEL_ID = "deterministic-structural-baseline"
A0_B2_REVISION = "A0_B2+B3+B4"
D1_LABELS = {
    "father role cue": "Word or short phrase denoting the role of father",
    "mother role cue": "Word or short phrase denoting the role of mother",
    "son role cue": "Word or short phrase denoting the role of son",
    "daughter role cue": "Word or short phrase denoting the role of daughter",
    "brother role cue": "Word or short phrase denoting the role of brother",
    "sister role cue": "Word or short phrase denoting the role of sister",
    "spouse role cue": "Word or short phrase denoting husband, wife, or spouse",
}

_NAME = r"(?-i:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-Za-zÀ-ÖØ-öø-ÿ'-]+)"
_KINSHIP = r"(?:pai|mãe|filho|filha|irmão|irmã|marido|esposa|cônjuge)"
_ENDPOINT = (
    rf"(?:uma\s+pessoa(?:\s+(?:que|cujo|não)\s+[^,.!?]+)?|alguém(?:\s+que\s+[^,.!?]+)?|"
    rf"(?:meu|minha)\s+{_KINSHIP}|ele|ela|dele|dela|meu|minha|{_NAME})"
)
_TERM = r"(?:pai|mãe|filho|filha|irmão|irmã|marido|esposa|cônjuge)"
_TYPE = {
    "pai": "FATHER_OF", "mãe": "MOTHER_OF", "filho": "SON_OF",
    "filha": "DAUGHTER_OF", "irmão": "BROTHER_OF", "irmã": "SISTER_OF",
    "marido": "SPOUSE_OF", "esposa": "SPOUSE_OF", "cônjuge": "SPOUSE_OF",
}
_UNRESOLVED = re.compile(r"^(?:ele|ela|dele|dela|quem|alguém|uma\s+pessoa)\b", re.I)
_REPORTING = re.compile(
    rf"(?P<speaker>{_NAME})\b[^.!?;]*?\b(?:disse|contou|afirmou|explicou|declarou|relatou|informou|comunicou|perguntou|negou)\b[^.!?;]*?\bque\b",
    re.I,
)
_SOURCE_REPORTING = re.compile(
    rf"(?:^|[,;]\s*)(?:segundo|de\s+acordo\s+com)\s+(?P<speaker>{_NAME})\s*,",
    re.I,
)
_REPORTED_QUESTION = re.compile(
    rf"(?P<speaker>{_NAME})\b[^.!?;]*?\bperguntou\b[^.!?;]*?\bse\b",
    re.I,
)
_CONFIG_HASH = hashlib.sha256(json.dumps({
    "pipeline": "LIFEGRAPH_PERSON_RELATION_V1",
    "families": ["direct", "reordered", "apposition", "relative_apposition", "contracted", "ter_como", "discontinuous", "coordination", "interrogative"],
    "guards": ["emphatic_negation", "uncertainty_and_question", "hypothetical", "reported_b4", "temporal"],
    "endpoint_targets": ["EXPLICIT_MENTION", "NARRATOR_ROLE", "UNRESOLVED_MENTION"],
}, sort_keys=True).encode()).hexdigest().upper()


@dataclass(frozen=True)
class Structure:
    """One relation interpretation grounded in a supported local construction."""

    family: str
    relation_type: str
    surface: str
    start: int
    end: int
    endpoint_a: str | None
    endpoint_a_start: int | None
    endpoint_a_end: int | None
    endpoint_b: str | None
    endpoint_b_start: int | None
    endpoint_b_end: int | None


def _structure(match: re.Match[str], family: str, *, reverse: bool = False, holder_role: bool = False) -> Structure:
    """Create a structure using named regex groups rather than proximity."""
    term = match.group("term").casefold()
    if holder_role:
        a_group, b_group = "role_person", "holder"
    elif reverse:
        a_group, b_group = "value", "object"
    else:
        a_group, b_group = "subject", "object"
    return Structure(
        family=family, relation_type=_TYPE[term], surface=match.group("surface"),
        start=match.start("surface"), end=match.end("surface"),
        endpoint_a=match.group(a_group), endpoint_a_start=match.start(a_group), endpoint_a_end=match.end(a_group),
        endpoint_b=match.group(b_group), endpoint_b_start=match.start(b_group), endpoint_b_end=match.end(b_group),
    )


def structural_relations(text: str) -> list[Structure]:
    """Parse only approved, local, family-level structural templates."""
    found: list[Structure] = []
    occupied: set[tuple[int, int, str, str | None, str | None]] = set()

    # Possessive relation predicates identify the narrator as a linguistic role,
    # never as a graph identity.  Endpoint B preserves the exact possessive token.
    narrator_predicate = re.compile(
        rf"\b(?P<value>{_NAME})\s+(?:não\s+|nunca\s+|jamais\s+)?"
        rf"(?:é|era|foi|seja|fosse|seria)\s+(?P<surface>(?P<possessive>meu|minha)\s+"
        rf"(?P<term>{_TERM}))\b", re.I)
    narrator_reordered = re.compile(
        rf"\b(?P<surface>(?P<possessive>Meu|Minha)\s+(?P<term>{_TERM}))\s+"
        rf"(?:é|era|foi)\s+(?P<value>{_NAME})\b", re.I)
    for family, pattern in (("narrator_predicate", narrator_predicate),
                            ("narrator_reordered", narrator_reordered)):
        for match in pattern.finditer(text):
            found.append(Structure(
                family, _TYPE[match.group("term").casefold()], match.group("surface"),
                match.start("surface"), match.end("surface"), match.group("value"),
                match.start("value"), match.end("value"), match.group("possessive"),
                match.start("possessive"), match.end("possessive"),
            ))

    # A relative apposition is accepted only with an explicit local head and
    # closing comma. Nested reporting clauses are handled by the ordinary direct
    # predicate and therefore never inherit the outer relative head.
    relative = re.compile(
        rf"\b(?P<subject>{_ENDPOINT})\s*,\s*que\s+"
        rf"(?:não\s+|nunca\s+|jamais\s+|talvez\s+)?"
        rf"(?:é|era|foi|seja)\s+(?:(?:o|a)\s+)?"
        rf"(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)\s*"
        rf"(?P<object>{_ENDPOINT})\s*,", re.I)
    relative_narrator = re.compile(
        rf"\b(?P<value>{_NAME})\s*,\s*que\s+"
        rf"(?:não\s+|nunca\s+|jamais\s+|talvez\s+)?"
        rf"(?:é|era|foi|seja)\s+"
        rf"(?P<surface>(?P<possessive>meu|minha)\s+(?P<term>{_TERM}))\s*,", re.I)
    for match in relative.finditer(text):
        found.append(_structure(match, "relative_apposition"))
    for match in relative_narrator.finditer(text):
        found.append(Structure(
            "relative_narrator", _TYPE[match.group("term").casefold()], match.group("surface"),
            match.start("surface"), match.end("surface"), match.group("value"),
            match.start("value"), match.end("value"), match.group("possessive"),
            match.start("possessive"), match.end("possessive"),
        ))

    # Interrogative templates retain relation mentions but never supply graph
    # identities. Their question mark is interpreted by the epistemic guard.
    focused_question = re.compile(
        rf"(?:^|[.!?]\s*)É\s+(?P<subject>{_NAME})\s+(?:o|a)\s+"
        rf"(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)\s*"
        rf"(?P<object>{_ENDPOINT})\s*\?", re.I)
    wh_question = re.compile(
        rf"(?:^|[.!?]\s*)(?P<subject>Quem)\s+é\s+(?:o|a)\s+"
        rf"(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)\s*"
        rf"(?P<object>{_ENDPOINT})\s*\?", re.I)
    for family, pattern in (("focused_question", focused_question), ("wh_question", wh_question)):
        for match in pattern.finditer(text):
            found.append(_structure(match, family))

    patterns: list[tuple[str, re.Pattern[str], dict]] = [
        ("reordered_possessive", re.compile(
            rf"\b(?:O|A)\s+(?P<surface>(?P<term>{_TERM}))\s+"
            rf"(?P<object>dele|dela)\s+(?:é|era|foi)\s+(?P<value>{_ENDPOINT})\b", re.I), {"reverse": True}),
        ("reordered", re.compile(
            rf"\b(?:O|A)\s+(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)\s*"
            rf"(?P<object>{_ENDPOINT})\s+(?:é|era|foi)\s+(?P<value>{_ENDPOINT})\b", re.I), {"reverse": True}),
        ("ter_como", re.compile(
            rf"\b(?P<holder>{_ENDPOINT})\s+tem\s+(?P<role_person>{_ENDPOINT})\s+como\s+"
            rf"(?P<surface>(?P<term>{_TERM}))\b(?!\s+(?:para|no|na|do|da)\b)", re.I), {"holder_role": True}),
        ("discontinuous", re.compile(
            rf"\b(?P<subject>{_ENDPOINT})\s+(?:é|era|foi)\s*,\s*"
            rf"segundo\s+(?:o\s+registro\s+familiar|os\s+documentos\s+da\s+família|ela\s+própria)\s*,\s*"
            rf"(?:(?:o|a)\s+)?(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)\s*(?P<object>{_ENDPOINT})\b", re.I), {}),
        ("direct_possessive", re.compile(
            rf"\b(?P<subject>{_ENDPOINT})\s+(?:é|era|foi)\s+(?:(?:o|a)\s+)?"
            rf"(?P<surface>(?P<term>{_TERM}))\s+(?P<object>dele|dela)\b", re.I), {}),
        ("direct", re.compile(
            rf"\b(?P<subject>{_ENDPOINT})\s+(?:não\s+|nunca\s+|jamais\s+)?"
            rf"(?:é|são|era|eram|foi|foram|seja|fosse|seria)\s+(?:(?:o|a)\s+)?"
            rf"(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)(?:\s+criação\s+de)?\s*(?P<object>{_ENDPOINT})\b", re.I), {}),
        ("apposition", re.compile(
            rf"\b(?P<subject>{_ENDPOINT})\s*,\s*(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)\s*"
            rf"(?P<object>{_ENDPOINT})\s*(?=,|\s+e\s+{_TERM}\s+d(?:e|a|o)\b)", re.I), {}),
    ]
    for family, pattern, options in patterns:
        for match in pattern.finditer(text):
            item = _structure(match, family, **options)
            if family == "apposition" and re.search(r",\s*que\b[^,]*$", text[:match.start()], re.I):
                # The nominal apposition is nested inside an open relative
                # clause, so its attachment is not safe without a parser.
                continue
            key = (item.start, item.end, item.relation_type, item.endpoint_a, item.endpoint_b)
            if key not in occupied:
                occupied.add(key)
                found.append(item)

    # A second relation in an appositive chain inherits only the explicit local head.
    chain = re.compile(
        rf"\b(?P<head>{_ENDPOINT})\s*,[^,.!?]*?\b{_TERM}\s+d(?:e|a|o)\b\s*{_ENDPOINT}\s+e\s+"
        rf"(?P<surface>(?P<term>{_TERM})\s+d(?:e|a|o)\b)\s*(?P<object>{_ENDPOINT})\s*,", re.I)
    for match in chain.finditer(text):
        item = Structure(
            "appositive_chain", _TYPE[match.group("term").casefold()], match.group("surface"),
            match.start("surface"), match.end("surface"), match.group("head"), match.start("head"),
            match.end("head"), match.group("object"), match.start("object"), match.end("object"),
        )
        key = (item.start, item.end, item.relation_type, item.endpoint_a, item.endpoint_b)
        if key not in occupied:
            occupied.add(key)
            found.append(item)

    # Expand a safely delimited two-name object coordination.
    expanded: list[Structure] = []
    for item in found:
        after = text[item.endpoint_b_end or item.end:]
        second = re.match(rf"\s+e\s+(?P<object>{_NAME})\b(?!\s+(?:é|era|foi|seja)\b)", after)
        expanded.append(item)
        if second and item.family in {"direct", "apposition"}:
            start = (item.endpoint_b_end or item.end) + second.start("object")
            expanded.append(Structure(
                "coordination", item.relation_type, item.surface, item.start, item.end,
                item.endpoint_a, item.endpoint_a_start, item.endpoint_a_end,
                second.group("object"), start, start + len(second.group("object")),
            ))
    # V1 does not factualize quoted examples or mentioned propositions.
    def quoted(position: int) -> bool:
        before = text[:position]
        return before.count('"') % 2 == 1 or before.count("“") > before.count("”")

    return sorted((item for item in expanded if not quoted(item.start)),
                  key=lambda x: (x.start, x.endpoint_b_start or -1, x.relation_type))


def detect_a0_b2(text: str) -> list[RelationDetection]:
    """Emit exact relation-cue evidence for every supported structural family."""
    seen: set[tuple[int, int, str]] = set()
    detections = []
    for item in structural_relations(text):
        key = (item.start, item.end, item.relation_type)
        if key not in seen:
            seen.add(key)
            detections.append(RelationDetection(text=text[item.start:item.end], start=item.start, end=item.end,
                                                label=item.relation_type, confidence=1.0))
    return detections


def adapt_gliner(raw: dict, threshold: float) -> list[RelationDetection]:
    """Adapt GLiNER entities without assigning linguistic or graph semantics."""
    return sorted([
        RelationDetection(text=span["text"], start=span["start"], end=span["end"], label=label,
                          confidence=float(span.get("confidence", 0.0)))
        for label, spans in raw.get("entities", {}).items()
        for span in (spans if isinstance(spans, list) else [])
        if float(span.get("confidence", 0.0)) >= threshold
    ], key=lambda x: (x.start, x.end, x.label))


def _supported_by_detection(item: Structure, detections: list[RelationDetection]) -> RelationDetection | None:
    """Require detector evidence to overlap the grounded role cue."""
    options = [d for d in detections if d.start < item.end and item.start < d.end]
    return max(options, key=lambda d: d.confidence) if options else None


def _guards(text: str, item: Structure) -> tuple[str, str, str, str, str | None]:
    """Evaluate independent, sentence-local safety dimensions."""
    left_boundary = max(text.rfind(mark, 0, item.start) for mark in ".!?;") + 1
    right_positions = [text.find(mark, item.end) for mark in ".!?;" if text.find(mark, item.end) >= 0]
    right_boundary = min(right_positions) + 1 if right_positions else len(text)
    sentence = text[left_boundary:right_boundary]
    left = text[left_boundary:item.start]
    reporting_matches = list(_REPORTING.finditer(left)) + list(_REPORTED_QUESTION.finditer(left))
    source_matches = list(_SOURCE_REPORTING.finditer(left))
    reporting = "REPORTED" if reporting_matches or source_matches else "DIRECT"
    source_match = (reporting_matches + source_matches)[-1] if reporting_matches or source_matches else None
    source = source_match.group("speaker") if source_match else None
    negated = bool(re.search(
        r"\b(?:não\s+(?:é|era|foi|seja)|nunca\s+foi|jamais\s+foi|de\s+jeito\s+nenhum|de\s+forma\s+alguma|em\s+hipótese\s+alguma|negou\s+que)\b",
        left, re.I))
    polarity = "NEGATED" if negated else "POSITIVE"
    if re.search(r"\b(?:se\b[^.!?;]*\bfosse|caso\b[^.!?;]*\bfosse|supondo\s+que[^.!?;]*\bfosse|seria\b[^.!?;]*\bse)\b", sentence, re.I):
        epistemic = "HYPOTHETICAL"
    elif "?" in sentence or re.search(
        r"\b(?:parece\s+que|é\s+possível\s+que|pode\s+ser\s+que|talvez|acho\s+que|acredito\s+que|não\s+tenho\s+certeza\s+se|há\s+dúvida\s+se|não\s+se\s+sabe\s+se|sem\s+certeza)\b",
        sentence, re.I):
        epistemic = "UNCERTAIN"
    else:
        epistemic = "ASSERTED"
    local = text[max(left_boundary, item.start - 100):min(right_boundary, item.end + 100)]
    temporal = "PAST" if re.search(r"\b(?:era|eram|foi|foram)\b", local, re.I) else "CURRENT_OR_UNSPECIFIED"
    return polarity, epistemic, reporting, temporal, source


def _eligibility(payload: dict) -> str:
    """Return the first deterministic linguistic blocker."""
    if payload["polarity"] == "NEGATED": return "NOT_PERSISTIBLE_NEGATED"
    if payload["epistemic_status"] == "HYPOTHETICAL": return "NOT_PERSISTIBLE_HYPOTHETICAL"
    if payload["epistemic_status"] == "UNCERTAIN": return "NOT_PERSISTIBLE_UNCERTAIN"
    if payload["reporting_mode"] == "REPORTED": return "NOT_PERSISTIBLE_REPORTED"
    if "UNRESOLVED_MENTION" in {payload["endpoint_a_resolution_state"], payload["endpoint_b_resolution_state"]}:
        return "NOT_PERSISTIBLE_PARTIAL_ENDPOINT"
    if payload["temporal_scope"] != "CURRENT_OR_UNSPECIFIED":
        return "NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE"
    return "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED"


def extract_relations_b2(text: str, source_reference: str, strategy: str, threshold: float = 0.5,
                         raw_gliner_output: dict | None = None) -> RelationExtractionResult:
    """Build candidates with common structural and guard logic for A0/B/C/D1."""
    structures = structural_relations(text)
    detections = detect_a0_b2(text) if strategy == "A0_B2" else adapt_gliner(raw_gliner_output or {}, threshold)
    candidates = []
    seen: set[tuple] = set()
    for item in structures:
        evidence = _supported_by_detection(item, detections)
        if evidence is None:
            continue
        key = (item.relation_type, item.start, item.endpoint_a, item.endpoint_b)
        if key in seen:
            continue
        seen.add(key)
        polarity, epistemic, reporting, temporal, reporting_source = _guards(text, item)
        a_state = "UNRESOLVED_MENTION" if item.endpoint_a is None or _UNRESOLVED.match(item.endpoint_a) else "RESOLVED_MENTION"
        b_state = "UNRESOLVED_MENTION" if item.endpoint_b is None or _UNRESOLVED.match(item.endpoint_b) else "RESOLVED_MENTION"
        a_target = "UNRESOLVED_MENTION" if a_state == "UNRESOLVED_MENTION" else "EXPLICIT_MENTION"
        b_target = "UNRESOLVED_MENTION" if b_state == "UNRESOLVED_MENTION" else "EXPLICIT_MENTION"
        if item.family in {"narrator_predicate", "narrator_reordered", "relative_narrator"}:
            b_target = "NARRATOR_ROLE"
        payload = {
            "candidate_id": hashlib.sha256(f"{source_reference}|{strategy}|{key}".encode()).hexdigest()[:32],
            "source_reference": source_reference, "source_text": text, "relation_type": item.relation_type,
            "relation_surface_text": item.surface, "relation_span_start": item.start, "relation_span_end": item.end,
            "endpoint_a_mention": item.endpoint_a, "endpoint_a_span_start": item.endpoint_a_start,
            "endpoint_a_span_end": item.endpoint_a_end, "endpoint_a_resolution_state": a_state,
            "endpoint_a_semantic_target": a_target,
            "endpoint_b_mention": item.endpoint_b, "endpoint_b_span_start": item.endpoint_b_start,
            "endpoint_b_span_end": item.endpoint_b_end, "endpoint_b_resolution_state": b_state,
            "endpoint_b_semantic_target": b_target,
            "polarity": polarity, "epistemic_status": epistemic, "reporting_mode": reporting,
            "reporting_source_mention": reporting_source, "temporal_scope": temporal,
            "warnings": [], "pipeline_id": PIPELINE_ID,
            "model_id": A0_B2_MODEL_ID if strategy == "A0_B2" else MODEL_ID,
            "model_revision": A0_B2_REVISION if strategy == "A0_B2" else MODEL_REVISION,
            "configuration_hash": _CONFIG_HASH, "detector_strategy": "A0" if strategy == "A0_B2" else strategy,
            "detector_label": evidence.label, "detector_confidence": evidence.confidence,
        }
        payload["persistence_eligibility"] = _eligibility(payload)
        candidates.append(RelationCandidate.model_validate(payload))
    return RelationExtractionResult(source_text=text, strategy="A0" if strategy == "A0_B2" else strategy,
                                    threshold=threshold, detections=detections, candidates=candidates)
