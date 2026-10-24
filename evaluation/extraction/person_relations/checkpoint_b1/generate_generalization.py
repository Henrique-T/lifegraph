"""Generate the reviewed Checkpoint B.1 generalization development corpus."""

from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "checkpoint_b1_generalization.jsonl"
RELATIONS = (
    ("FATHER_OF", "pai", "João", "Maria"),
    ("MOTHER_OF", "mãe", "Ana", "Pedro"),
    ("SON_OF", "filho", "Carlos", "Beatriz"),
    ("DAUGHTER_OF", "filha", "Luiza", "Roberto"),
    ("BROTHER_OF", "irmão", "Tiago", "Carla"),
    ("SISTER_OF", "irmã", "Helena", "Marcos"),
    ("SPOUSE_OF", "marido", "Rafael", "Sônia"),
)


def candidate(
    relation_type: str,
    surface: str,
    endpoint_a: str | None,
    endpoint_b: str | None,
    *,
    polarity: str = "POSITIVE",
    epistemic: str = "ASSERTED",
    reporting: str = "DIRECT",
    temporal: str = "CURRENT_OR_UNSPECIFIED",
    persistible: bool | None = None,
    rationale: str,
) -> dict:
    """Build one oracle candidate with the frozen compositional dimensions."""
    if persistible is None:
        persistible = bool(
            polarity == "POSITIVE"
            and epistemic == "ASSERTED"
            and reporting == "DIRECT"
            and temporal == "CURRENT_OR_UNSPECIFIED"
            and endpoint_a is not None
            and endpoint_b is not None
        )
    return {
        "relation_type": relation_type,
        "relation_surface_text": surface,
        "endpoint_a_mention": endpoint_a,
        "endpoint_b_mention": endpoint_b,
        "polarity": polarity,
        "epistemic_status": epistemic,
        "reporting_mode": reporting,
        "temporal_scope": temporal,
        "persistible_in_v1": persistible,
        "rationale": rationale,
    }


def generate() -> list[dict]:
    """Create diverse, hand-specified template families without held-out input."""
    cases: list[dict] = []

    def add(narrative: str, expected: list[dict], *tags: str) -> None:
        cases.append({
            "case_id": f"PR-{181 + len(cases):03d}",
            "narrative": narrative,
            "expected_relation_candidates": expected,
            "tags": ["b1_generalization", *tags],
        })

    # Reordered copular predicates: endpoint A follows the copula.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"O {term} de {b} é {a}.",
            [candidate(relation_type, surface, a, b, rationale="Reordered copular relation remains explicit.")],
            "reordered", "copular", "persistible_oracle",
        )

    # Possessive pronouns preserve text but do not justify antecedent resolution.
    for relation_type, term, a, _ in RELATIONS:
        add(
            f"{a} é o {term} dela.",
            [candidate(relation_type, term, a, "dela", persistible=False,
                       rationale="Possessive endpoint is explicit text but its antecedent is unresolved.")],
            "possessive", "pronoun", "partial_endpoint",
        )

    # Ter ... como is an explicit relation construction outside A0's original syntax.
    for relation_type, term, a, b in RELATIONS:
        add(
            f"{b} tem {a} como {term}.",
            [candidate(relation_type, term, a, b, rationale="The ter-como construction explicitly assigns the relation role.")],
            "existential_have", "reordered", "persistible_oracle",
        )

    # Appositions are explicit nominal assertions in V1.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"{a}, {term} de {b}, chegou cedo.",
            [candidate(relation_type, surface, a, b, rationale="A restrictive local apposition explicitly states the relation.")],
            "apposition", "persistible_oracle",
        )

    # Article and contracted-preposition variation.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} da" if b[-1].lower() == "a" else f"{term} do"
        article_b = b
        add(
            f"{a} é o {surface} {article_b}.",
            [candidate(relation_type, surface, a, article_b,
                       rationale="Contracted Portuguese preposition preserves the canonical relation.")],
            "contracted_preposition", "copular", "persistible_oracle",
        )

    # Discontinuous parenthetical modifiers stress span and endpoint recovery.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"{a} é, segundo os documentos da família, {term} de {b}.",
            [candidate(relation_type, surface, a, b,
                       rationale="Incidental parenthetical material does not turn the assertion into reported speech.")],
            "discontinuous", "distractor_heavy", "persistible_oracle",
        )

    # Coordination: one explicit relation expression can yield two binary candidates.
    for relation_type, term, a, b in RELATIONS:
        other = "Fernanda"
        surface = f"{term} de"
        add(
            f"{a} é {term} de {b} e {other}.",
            [
                candidate(relation_type, surface, a, b, rationale="First coordinated binary relation."),
                candidate(relation_type, surface, a, other, rationale="Second coordinated binary relation."),
            ],
            "coordination", "multiple_relations", "persistible_oracle",
        )

    # Appositive chains contain independently recoverable claims.
    for index, (relation_type, term, a, b) in enumerate(RELATIONS):
        other_type, other_term, _, other_b = RELATIONS[(index + 1) % len(RELATIONS)]
        surface = f"{term} de"
        other_surface = f"{other_term} de"
        add(
            f"{a}, {term} de {b} e {other_term} de {other_b}, chegou.",
            [
                candidate(relation_type, surface, a, b, rationale="First appositive relation."),
                candidate(other_type, other_surface, a, other_b, rationale="Second appositive relation."),
            ],
            "appositive_chain", "multiple_relations", "distractor_heavy",
        )

    # Reported and uncertain dimensions compose independently.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"Paulo explicou que talvez {a} seja {term} de {b}.",
            [candidate(relation_type, surface, a, b, epistemic="UNCERTAIN", reporting="REPORTED",
                       rationale="Reported speech and uncertainty are independent blockers.")],
            "reported", "uncertain", "embedded_clause", "speaker_distractor",
        )

    # Clear negation variants outside the original narrow markers.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"De jeito nenhum {a} é {term} de {b}.",
            [candidate(relation_type, surface, a, b, polarity="NEGATED",
                       rationale="Sentence-level emphatic negation scopes over the relation.")],
            "negated", "negation_variant",
        )

    # Clear uncertainty variants; no enum expansion is needed.
    uncertainty_prefixes = ("Parece que", "É possível que", "Há dúvida se", "Tudo indica, sem certeza, que", "Não se sabe se", "Talvez", "Pode ser que")
    for (relation_type, term, a, b), prefix in zip(RELATIONS, uncertainty_prefixes):
        surface = f"{term} de"
        add(
            f"{prefix} {a} seja {term} de {b}.",
            [candidate(relation_type, surface, a, b, epistemic="UNCERTAIN",
                       rationale="Explicit uncertainty prevents a direct asserted claim.")],
            "uncertain", "uncertainty_variant",
        )

    # Questions remain non-persistible uncertain candidates.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"É {a} o {term} de {b}?",
            [candidate(relation_type, surface, a, b, epistemic="UNCERTAIN",
                       rationale="Interrogative form is not an asserted positive claim.")],
            "question", "reordered",
        )

    # Quoted examples are negative controls and must not be factualized.
    for _, term, a, b in RELATIONS:
        add(
            f"O manual usa a frase \"{a} é {term} de {b}\" como exemplo.",
            [], "quoted_language", "no_relation", "negative_control",
        )

    # Incidental relational descriptions are not direct conversational claims.
    incidental_verbs = ("falou com", "encontrou", "telefonou para", "viu", "cumprimentou", "procurou", "ouviu")
    for (_, term, _, b), verb in zip(RELATIONS, incidental_verbs):
        add(
            f"Paulo {verb} o {term} de {b} ontem.",
            [], "incidental_kinship", "no_relation", "negative_control",
        )

    # Metaphorical and institutional uses are negative controls.
    metaphors = (
        "João é um pai para todos no time.",
        "Ana faz papel de mãe no projeto.",
        "Carlos é como um filho para Beatriz.",
        "Luiza é a filha preferida da empresa.",
        "Tiago trata Carla como irmão de equipe.",
        "Helena é como uma irmã para Marcos.",
        "Rafael virou o marido do escritório nas brincadeiras.",
    )
    for narrative in metaphors:
        add(narrative, [], "metaphor", "no_relation", "negative_control")

    # Many local distractors must not replace the structurally supported pair.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"Paulo contou a Renata, diante de Bruno e Clara, que {a} é {term} de {b}.",
            [candidate(relation_type, surface, a, b, reporting="REPORTED",
                       rationale="Only the embedded local subject and object are relation endpoints.")],
            "reported", "multiple_people", "distractor_heavy", "speaker_distractor",
        )

    # Ambiguous pronouns retain an unresolved linguistic endpoint.
    for relation_type, term, _, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"Paulo encontrou Renato e disse que ele é {term} de {b}.",
            [candidate(relation_type, surface, None, b, reporting="REPORTED", persistible=False,
                       rationale="The local pronoun has multiple plausible antecedents.")],
            "pronoun", "partial_endpoint", "ambiguous", "reported",
        )

    # Past relations remain review-only.
    for relation_type, term, a, b in RELATIONS:
        surface = f"{term} de"
        add(
            f"Durante muitos anos, {a} foi {term} de {b}.",
            [candidate(relation_type, surface, a, b, temporal="PAST",
                       rationale="Past copula marks unsupported historical scope for V1 persistence.")],
            "past", "temporal_scope",
        )

    # Explicit event-only statements remain outside relation extraction.
    event_controls = (
        "João se casou com Maria em 2019.",
        "Ana deu à luz Pedro em 2001.",
        "Carlos nasceu em 1990.",
        "Luiza participou do casamento de Roberto.",
        "Tiago registrou o nascimento de Carla.",
        "Helena ficou viúva em 2020.",
        "Rafael compareceu ao casamento de Sônia.",
    )
    for narrative in event_controls:
        add(narrative, [], "event_only", "no_relation", "negative_control")

    assert len(cases) == 133
    return cases


def main() -> None:
    """Write deterministic UTF-8 JSON Lines and report aggregate size."""
    cases = generate()
    OUTPUT.write_text(
        "".join(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n" for case in cases),
        encoding="utf-8",
    )
    print(json.dumps({
        "file": str(OUTPUT),
        "narratives": len(cases),
        "candidates": sum(len(case["expected_relation_candidates"]) for case in cases),
    }))


if __name__ == "__main__":
    main()
