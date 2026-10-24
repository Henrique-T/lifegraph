"""Author the B.4 micro-challenge without importing the extractor."""

from __future__ import annotations

import json
from pathlib import Path


def rel(kind, surface, a, b, *, polarity="POSITIVE", epistemic="ASSERTED", reporting="DIRECT",
        temporal="CURRENT_OR_UNSPECIFIED", a_target="EXPLICIT_MENTION",
        b_target="EXPLICIT_MENTION", interrogative=False, rationale="Explicit V1 relation mention."):
    persistible = (
        not interrogative and polarity == "POSITIVE" and epistemic == "ASSERTED"
        and reporting == "DIRECT" and temporal == "CURRENT_OR_UNSPECIFIED"
        and a_target != "UNRESOLVED_MENTION" and b_target != "UNRESOLVED_MENTION"
    )
    return {
        "relation_type": kind, "relation_surface_text": surface,
        "endpoint_a_mention": a, "endpoint_b_mention": b,
        "endpoint_a_semantic_target": a_target, "endpoint_b_semantic_target": b_target,
        "polarity": polarity, "epistemic_status": epistemic, "reporting_mode": reporting,
        "temporal_scope": temporal, "interrogative": interrogative,
        "persistible_in_v1": persistible, "rationale": rationale,
    }


def case(index, text, expected, tags):
    return {"case_id": f"B4-U-{index:03d}", "narrative": text,
            "expected_relation_candidates": expected, "tags": tags}


CASES = [
    case(1, "Marcos, que é pai de Elisa, trabalha aqui.", [rel("FATHER_OF", "pai de", "Marcos", "Elisa")], ["relative_apposition", "direct", "parent_child"]),
    case(2, "Helena, que não é mãe de Caio, respondeu.", [rel("MOTHER_OF", "mãe de", "Helena", "Caio", polarity="NEGATED")], ["relative_apposition", "negated", "parent_child"]),
    case(3, "Bruno, que talvez seja filho de Marta, chegou.", [rel("SON_OF", "filho de", "Bruno", "Marta", epistemic="UNCERTAIN")], ["relative_apposition", "uncertain", "parent_child"]),
    case(4, "Clara, que foi filha de Paulo, mudou-se.", [rel("DAUGHTER_OF", "filha de", "Clara", "Paulo", temporal="PAST")], ["relative_apposition", "past", "parent_child"]),
    case(5, "André, que é irmão da Beatriz, telefonou.", [rel("BROTHER_OF", "irmão da", "André", "Beatriz")], ["relative_apposition", "contracted_preposition", "sibling"]),
    case(6, "Sara, que é minha irmã, voltou.", [rel("SISTER_OF", "minha irmã", "Sara", "minha", b_target="NARRATOR_ROLE")], ["relative_apposition", "narrator", "sibling"]),
    case(7, "Denise, que relatou que Otávio foi marido de Alice, saiu.", [rel("SPOUSE_OF", "marido de", "Otávio", "Alice", reporting="REPORTED", temporal="PAST")], ["relative_apposition", "nested_reporting", "reported", "spouse_surface"]),
    case(8, "Tiago, que disse a Laura que Renato é pai de Bia, chegou.", [rel("FATHER_OF", "pai de", "Renato", "Bia", reporting="REPORTED")], ["relative_apposition", "nested_reporting", "distractor_heavy", "parent_child"]),
    case(9, "João, que falou com o pai de Maria, saiu.", [], ["relative_control", "incidental_kinship", "no_relation"]),
    case(10, "Ana, que conhece Carla, irmã de Rui, voltou.", [], ["relative_control", "ambiguous_attachment", "no_relation"]),

    case(11, "João é pai de Maria?", [rel("FATHER_OF", "pai de", "João", "Maria", epistemic="UNCERTAIN", interrogative=True)], ["question", "yes_no", "parent_child"]),
    case(12, "É Ana a mãe de Pedro?", [rel("MOTHER_OF", "mãe de", "Ana", "Pedro", epistemic="UNCERTAIN", interrogative=True)], ["question", "focused", "parent_child"]),
    case(13, "Quem é o filho de Teresa?", [rel("SON_OF", "filho de", "Quem", "Teresa", epistemic="UNCERTAIN", a_target="UNRESOLVED_MENTION", interrogative=True)], ["question", "wh", "safe_abstention", "parent_child"]),
    case(14, "Será que ela é filha de César?", [rel("DAUGHTER_OF", "filha de", "ela", "César", epistemic="UNCERTAIN", a_target="UNRESOLVED_MENTION", interrogative=True)], ["question", "modal", "pronoun", "safe_abstention", "parent_child"]),
    case(15, "Lia perguntou se Ivo é irmão de Sara?", [rel("BROTHER_OF", "irmão de", "Ivo", "Sara", epistemic="UNCERTAIN", reporting="REPORTED", interrogative=True)], ["question", "reported", "sibling"]),
    case(16, "Eva não é irmã de Hugo?", [rel("SISTER_OF", "irmã de", "Eva", "Hugo", polarity="NEGATED", epistemic="UNCERTAIN", interrogative=True)], ["question", "negated", "sibling"]),
    case(17, "Marta perguntou sobre o marido de Rosa?", [], ["question", "incidental_kinship", "no_relation"]),
    case(18, "Quem é o cônjuge de Raul?", [rel("SPOUSE_OF", "cônjuge de", "Quem", "Raul", epistemic="UNCERTAIN", a_target="UNRESOLVED_MENTION", interrogative=True)], ["question", "wh", "safe_abstention", "spouse_surface"]),

    case(19, "Davi é pai de Laura.", [rel("FATHER_OF", "pai de", "Davi", "Laura")], ["direct", "parent_child"]),
    case(20, "Mônica é mãe de Bento.", [rel("MOTHER_OF", "mãe de", "Mônica", "Bento")], ["direct", "parent_child"]),
    case(21, "Caio é filho de Noemi.", [rel("SON_OF", "filho de", "Caio", "Noemi")], ["direct", "parent_child"]),
    case(22, "Paula é irmã de Leandro.", [rel("SISTER_OF", "irmã de", "Paula", "Leandro")], ["direct", "sibling"]),
    case(23, "Rosa é esposa de Raul.", [rel("SPOUSE_OF", "esposa de", "Rosa", "Raul")], ["direct", "spouse_surface"]),

    case(24, "A frase \"Carlos é pai de Luana\" consta no exemplo.", [], ["quotation", "no_relation"]),
    case(25, "Pedro virou o pai do projeto?", [], ["question", "metaphor", "no_relation"]),
    case(26, "Marina se casou com Otávio em 2020.", [], ["event_only", "no_relation"]),
]


if __name__ == "__main__":
    destination = Path(__file__).with_name("checkpoint_b4_unseen.jsonl")
    destination.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in CASES), encoding="utf-8")
    print(destination)
