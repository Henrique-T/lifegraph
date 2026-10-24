"""Hybrid, development-only Person-Relation V1 extraction pipeline."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from app.model import MODEL_ID, MODEL_REVISION
from app.relation_schemas import (
    RelationCandidate,
    RelationDetection,
    RelationExtractionResult,
)

PIPELINE_ID = "LIFEGRAPH_PT_RELATION_V1_DEV"
A0_MODEL_ID = "deterministic-lexical-baseline"
A0_MODEL_REVISION = "A0_V1"

SPECIFIC_LABELS = {
    "father relation": "Explicit words stating that one person is the father of another person",
    "mother relation": "Explicit words stating that one person is the mother of another person",
    "son relation": "Explicit words stating that one person is the son of another person",
    "daughter relation": "Explicit words stating that one person is the daughter of another person",
    "sibling relation": "Explicit words stating that one person is a brother or sister of another person",
    "spouse relation": "Explicit words stating that one person is a husband, wife, or spouse of another person",
}
GENERIC_LABELS = {
    "person relationship expression": "Explicit phrase that states a family or spouse relationship between people"
}

_WORD = r"[A-Za-zÀ-ÖØ-öø-ÿ�]+"
_SURFACES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:meu\s+)?pai\s+de\b|\bmeu\s+pai\b", re.I), "FATHER_OF"),
    (re.compile(r"\b(?:minha\s+)?m[ã�]e\s+de\b|\bminha\s+m[ã�]e\b", re.I), "MOTHER_OF"),
    (re.compile(r"\b(?:meu\s+)?filho\s+de\b|\bmeu\s+filho\b", re.I), "SON_OF"),
    (re.compile(r"\b(?:minha\s+)?filha\s+de\b|\bminha\s+filha\b", re.I), "DAUGHTER_OF"),
    (re.compile(r"\b(?:meu\s+)?irm[ã�]o\s+de\b|\bmeu\s+irm[ã�]o\b", re.I), "BROTHER_OF"),
    (re.compile(r"\b(?:minha\s+)?irm[ã�]\s+de\b|\bminha\s+irm[ã�]\b", re.I), "SISTER_OF"),
    (re.compile(r"\b(?:meu\s+)?(?:marido|esposo)\s+de\b|\bmeu\s+(?:marido|esposo)\b", re.I), "SPOUSE_OF"),
    (re.compile(r"\b(?:minha\s+)?esposa\s+de\b|\bminha\s+esposa\b", re.I), "SPOUSE_OF"),
    (re.compile(r"\bc[ô�]njuge\s+de\b", re.I), "SPOUSE_OF"),
    (re.compile(r"\bpai\s+de\b", re.I), "FATHER_OF"),
    (re.compile(r"\bm[ã�]e\s+de\b", re.I), "MOTHER_OF"),
    (re.compile(r"\bfilho\s+de\b", re.I), "SON_OF"),
    (re.compile(r"\bfilha\s+de\b", re.I), "DAUGHTER_OF"),
    (re.compile(r"\birm[ã�]o\s+de\b", re.I), "BROTHER_OF"),
    (re.compile(r"\birm[ã�]\s+de\b", re.I), "SISTER_OF"),
    (re.compile(r"\b(?:marido|esposo|esposa|c[ô�]njuge)\s+de\b", re.I), "SPOUSE_OF"),
)
_COPULA = re.compile(
    r"\b(?P<neg>n[ã�]o\s+|nunca\s+)?(?P<verb>é|são|era|eram|foi|foram|seja|sejam|fosse|fossem|seria|seriam|pode\s+ser)\s+(?:(?:o|a|um|uma)\s+)?$",
    re.I,
)
_REPORTING = re.compile(
    rf"(?P<speaker>{_WORD})\s+(?:disse|contou|afirmou|declarou|escreveu|perguntou|negou)\b[^.!?;]*?\bque\b",
    re.I,
)
_UNRESOLVED_ENDPOINT = re.compile(
    r"^(?:ele|ela|algu[ée]m|uma\s+pessoa|um\s+homem|uma\s+mulher)\b", re.I
)
_CONFIG_PAYLOAD = {
    "pipeline": PIPELINE_ID,
    "specific_labels": SPECIFIC_LABELS,
    "generic_labels": GENERIC_LABELS,
    "normalizer": "EXPLICIT_LEXICAL_V1",
    "endpoint_association": "LOCAL_COPULAR_V1",
    "guards": "COMPOSITIONAL_GUARDS_V1",
}
CONFIGURATION_HASH = hashlib.sha256(
    json.dumps(_CONFIG_PAYLOAD, sort_keys=True, ensure_ascii=False).encode("utf-8")
).hexdigest().upper()


@dataclass(frozen=True)
class NormalizedRelation:
    """Auditable normalization of one detector span."""

    relation_type: str
    surface: str
    start: int
    end: int


def _inside_quotes(text: str, position: int) -> bool:
    """Return whether a position is inside unmatched straight or curly quotes."""

    before = text[:position]
    return before.count('"') % 2 == 1 or before.count("“") > before.count("”")


def _sentence_bounds(text: str, position: int) -> tuple[int, int]:
    """Return sentence-local half-open boundaries."""

    start = max(text.rfind(mark, 0, position) for mark in ".!?") + 1
    ends = [text.find(mark, position) for mark in ".!?" if text.find(mark, position) >= 0]
    return start, min(ends) if ends else len(text)


def normalize_relation_span(text: str, detection: RelationDetection) -> NormalizedRelation | None:
    """Normalize only an approved lexical form overlapping detector evidence."""

    window_start = max(0, detection.start - 8)
    window_end = min(len(text), detection.end + 8)
    matches: list[NormalizedRelation] = []
    for pattern, relation_type in _SURFACES:
        for match in pattern.finditer(text, window_start, window_end):
            if match.start() < detection.end and detection.start < match.end():
                matches.append(
                    NormalizedRelation(
                        relation_type=relation_type,
                        surface=match.group(0),
                        start=match.start(),
                        end=match.end(),
                    )
                )
    if not matches:
        return None
    return min(matches, key=lambda item: (item.end - item.start, item.start, item.relation_type))


def _claim_context(text: str, normalized: NormalizedRelation) -> bool:
    """Reject quotation, meta-language, incidental kinship, and non-claims."""

    if _inside_quotes(text, normalized.start):
        return False
    sentence_start, _ = _sentence_bounds(text, normalized.start)
    left = text[sentence_start:normalized.start]
    if re.search(r"\b(?:frase|palavras?|express[ã�]o|campo\s+chamado)\b", left, re.I):
        return False
    if _COPULA.search(left):
        return True
    # Repeated coordinated predicates may omit the already established subject/copula.
    if re.search(r"\be\s*$", left, re.I):
        earlier = left[: re.search(r"\be\s*$", left, re.I).start()]
        return any(pattern.search(earlier) for pattern, _ in _SURFACES)
    return False


def detect_a0(text: str) -> list[RelationDetection]:
    """Detect inspectable lexical relation evidence in direct claim structures."""

    detections: list[RelationDetection] = []
    seen: set[tuple[int, int]] = set()
    for pattern, relation_type in _SURFACES:
        for match in pattern.finditer(text):
            key = (match.start(), match.end())
            normalized = NormalizedRelation(relation_type, match.group(0), *key)
            if key in seen or not _claim_context(text, normalized):
                continue
            seen.add(key)
            detections.append(
                RelationDetection(
                    text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    label=relation_type,
                    confidence=1.0,
                )
            )
    return sorted(detections, key=lambda item: (item.start, item.end, item.label))


def gliner_detections(raw: dict, threshold: float) -> list[RelationDetection]:
    """Adapt entity output from either GLiNER detector configuration."""

    detections: list[RelationDetection] = []
    for label, spans in raw.get("entities", {}).items():
        for span in spans if isinstance(spans, list) else []:
            confidence = float(span.get("confidence", 0.0))
            if confidence < threshold:
                continue
            detections.append(
                RelationDetection(
                    text=span["text"],
                    start=span["start"],
                    end=span["end"],
                    label=label,
                    confidence=confidence,
                )
            )
    return sorted(detections, key=lambda item: (item.start, item.end, item.label))


def _trim_fragment(fragment: str, absolute_start: int) -> tuple[str | None, int | None, int | None]:
    """Extract a local endpoint phrase without resolving graph identity."""

    leading = len(fragment) - len(fragment.lstrip())
    value = fragment.strip(" \t,;:")
    start = absolute_start + leading
    if not value:
        return None, None, None
    # Remove modality/reporting material before the final local subject.
    for marker in (" que ", ";", ","):
        if marker in value:
            offset = value.rfind(marker) + len(marker)
            start += offset
            value = value[offset:].strip()
    value = re.sub(
        r"^(?:acho\s+que|acredito\s+que|talvez|se|supondo\s+que|ser[á�]\s+que)\s+",
        "",
        value,
        flags=re.I,
    )
    # Keep explicit possessive kinship NPs; otherwise use the final local token.
    possessive = re.search(
        r"(?:meu|minha)\s+(?:pai|m[ã�]e|filho|filha|irm[ã�]o|irm[ã�]|marido|esposa)$",
        value,
        re.I,
    )
    if possessive:
        start += possessive.start()
        value = possessive.group(0)
    else:
        token = re.search(rf"(?:{_WORD}|ele|ela)$", value, re.I)
        if token:
            start += token.start()
            value = token.group(0)
    return value, start, start + len(value)


def _object_fragments(text: str, normalized: NormalizedRelation, sentence_end: int) -> list[tuple[str, int, int]]:
    """Extract one or more coordinated endpoint-B phrases."""

    surface_cf = normalized.surface.casefold()
    if not surface_cf.endswith(" de"):
        # Predicate possessive forms: Carlos é meu pai -> narrator mention "meu".
        possessive = re.match(r"(meu|minha)\b", normalized.surface, re.I)
        if possessive:
            return [(possessive.group(0), normalized.start, normalized.start + len(possessive.group(0)))]
        return []
    tail = text[normalized.end:sentence_end]
    tail = re.split(r"[,;]", tail, maxsplit=1)[0]
    creation = re.match(r"\s*cria[ç�][ã�]o\s+de\s+", tail, re.I)
    if creation:
        tail = tail[creation.end():]
        base = normalized.end + creation.end()
    else:
        base = normalized.end
    values: list[tuple[str, int, int]] = []
    # A simple coordinated name list represents multiple binary candidates.
    name_pair = re.match(rf"\s*({_WORD})\s+e\s+({_WORD})\s*$", tail)
    if name_pair:
        for group in (1, 2):
            values.append((name_pair.group(group), base + name_pair.start(group), base + name_pair.end(group)))
        return values
    match = re.match(
        rf"\s*(uma\s+pessoa[^.!?,;]*|um\s+homem[^.!?,;]*|uma\s+mulher[^.!?,;]*|algu[ée]m[^.!?,;]*|{_WORD})",
        tail,
        re.I,
    )
    if match:
        values.append((match.group(1).strip(), base + match.start(1), base + match.end(1)))
    return values


def _guards(text: str, normalized: NormalizedRelation) -> tuple[str, str, str, str, str | None]:
    """Apply compositional polarity, epistemic, reporting, and temporal guards."""

    sentence_start, sentence_end = _sentence_bounds(text, normalized.start)
    sentence = text[sentence_start:sentence_end + 1]
    left = text[sentence_start:normalized.start]
    reporting_matches = list(_REPORTING.finditer(left))
    reporting = "REPORTED" if reporting_matches else "DIRECT"
    reporting_source = reporting_matches[-1].group("speaker") if reporting_matches else None
    polarity = "NEGATED" if re.search(r"\b(?:n[ã�]o\s+(?:é|era|foi|seja)|nunca\s+foi|negou\s+que)\b", left, re.I) else "POSITIVE"
    if re.search(r"\b(?:se\b[^.!?]*\bfosse|supondo\s+que|seria\b[^.!?]*\bse)\b", sentence, re.I):
        epistemic = "HYPOTHETICAL"
    elif (
        "?" in sentence
        or re.search(r"\b(?:acho\s+que|acredito\s+que|talvez|pode\s+ser|n[ã�]o\s+tenho\s+certeza|ser[á�]\s+que)\b", sentence, re.I)
    ):
        epistemic = "UNCERTAIN"
    else:
        epistemic = "ASSERTED"
    copula = _COPULA.search(left)
    if copula and copula.group("verb").casefold() in {"era", "eram", "foi", "foram"}:
        temporal = "PAST"
    elif copula:
        temporal = "CURRENT_OR_UNSPECIFIED"
    else:
        temporal = "UNRESOLVED"
    return polarity, epistemic, reporting, temporal, reporting_source


def _eligibility_reason(candidate: dict) -> str:
    """Mirror the linguistic portion of the frozen V1 persistence predicate."""

    if candidate["polarity"] == "NEGATED":
        return "NOT_PERSISTIBLE_NEGATED"
    if candidate["epistemic_status"] == "HYPOTHETICAL":
        return "NOT_PERSISTIBLE_HYPOTHETICAL"
    if candidate["epistemic_status"] == "UNCERTAIN":
        return "NOT_PERSISTIBLE_UNCERTAIN"
    if candidate["reporting_mode"] == "REPORTED":
        return "NOT_PERSISTIBLE_REPORTED"
    if "UNRESOLVED_MENTION" in {
        candidate["endpoint_a_resolution_state"], candidate["endpoint_b_resolution_state"]
    }:
        return "NOT_PERSISTIBLE_PARTIAL_ENDPOINT"
    if candidate["temporal_scope"] != "CURRENT_OR_UNSPECIFIED":
        return "NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE"
    return "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED"


def build_candidates(
    text: str,
    source_reference: str,
    strategy: str,
    detections: list[RelationDetection],
) -> list[RelationCandidate]:
    """Run shared normalization, endpoint association, and safety guards."""

    candidates: list[RelationCandidate] = []
    carried_subject: tuple[str, int, int] | None = None
    carried_guards: tuple[str, str, str, str, str | None] | None = None
    seen: set[tuple[str, int, int, str | None, str | None]] = set()
    for detection in detections:
        normalized = normalize_relation_span(text, detection)
        if normalized is None or not _claim_context(text, normalized):
            continue
        sentence_start, sentence_end = _sentence_bounds(text, normalized.start)
        left = text[sentence_start:normalized.start]
        copula = _COPULA.search(left)
        if copula:
            endpoint_a = _trim_fragment(left[:copula.start()], sentence_start)
            carried_subject = endpoint_a if endpoint_a[0] else None
        elif re.search(r"\be\s*$", left, re.I) and carried_subject:
            endpoint_a = carried_subject
        else:
            endpoint_a = (None, None, None)
        objects = _object_fragments(text, normalized, sentence_end) or [(None, None, None)]
        guard_values = _guards(text, normalized)
        if copula:
            carried_guards = guard_values
        elif carried_guards and re.search(r"\be\s*$", left, re.I):
            guard_values = carried_guards
        polarity, epistemic, reporting, temporal, reporting_source = guard_values
        for endpoint_b in objects:
            a_text, a_start, a_end = endpoint_a
            b_text, b_start, b_end = endpoint_b
            a_state = "UNRESOLVED_MENTION" if a_text is None or _UNRESOLVED_ENDPOINT.match(a_text) else "RESOLVED_MENTION"
            b_state = "UNRESOLVED_MENTION" if b_text is None or _UNRESOLVED_ENDPOINT.match(b_text) else "RESOLVED_MENTION"
            key = (normalized.relation_type, normalized.start, normalized.end, a_text, b_text)
            if key in seen:
                continue
            seen.add(key)
            payload = {
                "candidate_id": hashlib.sha256(f"{source_reference}|{strategy}|{key}".encode("utf-8")).hexdigest()[:32],
                "source_reference": source_reference,
                "source_text": text,
                "relation_type": normalized.relation_type,
                "relation_surface_text": normalized.surface,
                "relation_span_start": normalized.start,
                "relation_span_end": normalized.end,
                "endpoint_a_mention": a_text,
                "endpoint_a_span_start": a_start,
                "endpoint_a_span_end": a_end,
                "endpoint_a_resolution_state": a_state,
                "endpoint_b_mention": b_text,
                "endpoint_b_span_start": b_start,
                "endpoint_b_span_end": b_end,
                "endpoint_b_resolution_state": b_state,
                "polarity": polarity,
                "epistemic_status": epistemic,
                "reporting_mode": reporting,
                "reporting_source_mention": reporting_source,
                "temporal_scope": temporal,
                "warnings": [],
                "pipeline_id": PIPELINE_ID,
                "model_id": A0_MODEL_ID if strategy == "A0" else MODEL_ID,
                "model_revision": A0_MODEL_REVISION if strategy == "A0" else MODEL_REVISION,
                "configuration_hash": CONFIGURATION_HASH,
                "detector_strategy": strategy,
                "detector_label": detection.label,
                "detector_confidence": detection.confidence,
            }
            payload["persistence_eligibility"] = _eligibility_reason(payload)
            candidates.append(RelationCandidate.model_validate(payload))
    return candidates


def extract_relations(
    text: str,
    source_reference: str,
    strategy: str,
    threshold: float = 0.5,
    raw_gliner_output: dict | None = None,
) -> RelationExtractionResult:
    """Execute A0 or adapt B/C model output through the shared pipeline."""

    if strategy == "A0":
        detections = detect_a0(text)
    elif strategy in {"B", "C"} and raw_gliner_output is not None:
        detections = gliner_detections(raw_gliner_output, threshold)
    else:
        raise ValueError("B/C extraction requires raw GLiNER output")
    return RelationExtractionResult(
        source_text=text,
        strategy=strategy,
        threshold=threshold,
        detections=detections,
        candidates=build_candidates(text, source_reference, strategy, detections),
    )
