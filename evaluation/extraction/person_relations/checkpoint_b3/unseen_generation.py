"""Author the one-shot B.3 development challenge before prediction.

This file contains oracle-authored cases only. It never imports or executes the
relation extraction pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path


def relation(relation_type, surface, a, b, *, polarity="POSITIVE", epistemic="ASSERTED",
             reporting="DIRECT", temporal="CURRENT_OR_UNSPECIFIED", a_target="EXPLICIT_MENTION",
             b_target="EXPLICIT_MENTION", rationale="Explicit relation under the stated modifiers."):
    persistible = (
        polarity == "POSITIVE" and epistemic == "ASSERTED" and reporting == "DIRECT"
        and temporal == "CURRENT_OR_UNSPECIFIED"
        and a_target != "UNRESOLVED_MENTION" and b_target != "UNRESOLVED_MENTION"
    )
    return {
        "relation_type": relation_type, "relation_surface_text": surface,
        "endpoint_a_mention": a, "endpoint_b_mention": b,
        "endpoint_a_semantic_target": a_target, "endpoint_b_semantic_target": b_target,
        "polarity": polarity, "epistemic_status": epistemic,
        "reporting_mode": reporting, "temporal_scope": temporal,
        "persistible_in_v1": persistible, "rationale": rationale,
    }


def case(number, narrative, candidates, tags):
    return {"case_id": f"B3-U-{number:03d}", "narrative": narrative,
            "expected_relation_candidates": candidates, "tags": tags}


CASES = [
    case(1, "Segundo Tiago, o pai de Lúcia é Marcos.", [relation("FATHER_OF", "pai de", "Marcos", "Lúcia", reporting="REPORTED")], ["reordered", "reported", "parent_child"]),
    case(2, "De acordo com Nádia, a mãe de Caio é Helena.", [relation("MOTHER_OF", "mãe de", "Helena", "Caio", reporting="REPORTED")], ["reordered", "reported", "parent_child"]),
    case(3, "Segundo Raul, o filho de Marta é Bruno.", [relation("SON_OF", "filho de", "Bruno", "Marta", reporting="REPORTED")], ["reordered", "reported", "parent_child"]),
    case(4, "De acordo com Elisa, a filha de Paulo é Clara.", [relation("DAUGHTER_OF", "filha de", "Clara", "Paulo", reporting="REPORTED")], ["reordered", "reported", "parent_child"]),
    case(5, "Segundo Laura, o irmão de Bia é André.", [relation("BROTHER_OF", "irmão de", "André", "Bia", reporting="REPORTED")], ["reordered", "reported", "sibling"]),
    case(6, "De acordo com Ivo, a irmã de Hugo é Sara.", [relation("SISTER_OF", "irmã de", "Sara", "Hugo", reporting="REPORTED")], ["reordered", "reported", "sibling"]),
    case(7, "Segundo Denise, o marido de Alice é Otávio.", [relation("SPOUSE_OF", "marido de", "Otávio", "Alice", reporting="REPORTED")], ["reordered", "reported", "spouse_surface"]),

    case(8, "Rafael, que não é pai de Luana, saiu cedo.", [relation("FATHER_OF", "pai de", "Rafael", "Luana", polarity="NEGATED")], ["apposition", "negated", "parent_child"]),
    case(9, "Bianca, que jamais foi mãe de Davi, respondeu.", [relation("MOTHER_OF", "mãe de", "Bianca", "Davi", polarity="NEGATED", temporal="PAST")], ["apposition", "emphatic_negation", "past", "parent_child"]),
    case(10, "Talvez Miguel seja filho da Renata.", [relation("SON_OF", "filho da", "Miguel", "Renata", epistemic="UNCERTAIN")], ["contracted_preposition", "uncertain", "parent_child"]),
    case(11, "É possível que Júlia seja filha do César.", [relation("DAUGHTER_OF", "filha do", "Júlia", "César", epistemic="UNCERTAIN")], ["contracted_preposition", "uncertain", "parent_child"]),
    case(12, "Parece que Leandro é irmão da Paula.", [relation("BROTHER_OF", "irmão da", "Leandro", "Paula", epistemic="UNCERTAIN")], ["contracted_preposition", "uncertain", "sibling"]),
    case(13, "Pode ser que Sílvia seja irmã do Mateus.", [relation("SISTER_OF", "irmã do", "Sílvia", "Mateus", epistemic="UNCERTAIN")], ["contracted_preposition", "uncertain", "sibling"]),
    case(14, "Não tenho certeza se Vítor é marido da Rosa.", [relation("SPOUSE_OF", "marido da", "Vítor", "Rosa", epistemic="UNCERTAIN")], ["contracted_preposition", "uncertain", "spouse_surface"]),

    case(15, "Lia relatou que Marina tem Jorge como pai.", [relation("FATHER_OF", "pai", "Jorge", "Marina", reporting="REPORTED")], ["ter_como", "reported", "parent_child"]),
    case(16, "Rui informou que Fábio tem Teresa como mãe.", [relation("MOTHER_OF", "mãe", "Teresa", "Fábio", reporting="REPORTED")], ["ter_como", "reported", "parent_child"]),
    case(17, "Eva declarou que Teresa tem Bento como filho.", [relation("SON_OF", "filho", "Bento", "Teresa", reporting="REPORTED")], ["ter_como", "reported", "parent_child"]),
    case(18, "Noemi contou que Artur tem Célia como filha.", [relation("DAUGHTER_OF", "filha", "Célia", "Artur", reporting="REPORTED")], ["ter_como", "reported", "parent_child"]),
    case(19, "Dora explicou que Lívia tem Mauro como irmão.", [relation("BROTHER_OF", "irmão", "Mauro", "Lívia", reporting="REPORTED")], ["ter_como", "reported", "sibling"]),
    case(20, "Caio afirmou que Breno tem Flávia como irmã.", [relation("SISTER_OF", "irmã", "Flávia", "Breno", reporting="REPORTED")], ["ter_como", "reported", "sibling"]),
    case(21, "Lúcia disse que Marta tem Raul como marido.", [relation("SPOUSE_OF", "marido", "Raul", "Marta", reporting="REPORTED")], ["ter_como", "reported", "spouse_surface"]),

    case(22, "João era, segundo o registro familiar, pai de Mirela.", [relation("FATHER_OF", "pai de", "João", "Mirela", temporal="PAST")], ["discontinuous", "past", "parent_child"]),
    case(23, "Ana foi, segundo os documentos da família, mãe de Lucas.", [relation("MOTHER_OF", "mãe de", "Ana", "Lucas", temporal="PAST")], ["discontinuous", "past", "parent_child"]),
    case(24, "Pedro era, segundo o registro familiar, irmão de Marta.", [relation("BROTHER_OF", "irmão de", "Pedro", "Marta", temporal="PAST")], ["discontinuous", "past", "sibling"]),
    case(25, "Carla foi, segundo os documentos da família, esposa de Luís.", [relation("SPOUSE_OF", "esposa de", "Carla", "Luís", temporal="PAST")], ["discontinuous", "past", "spouse_surface"]),

    case(26, "João é meu pai.", [relation("FATHER_OF", "meu pai", "João", "meu", b_target="NARRATOR_ROLE")], ["direct", "narrator", "possessive", "parent_child"]),
    case(27, "Minha mãe é Alice.", [relation("MOTHER_OF", "Minha mãe", "Alice", "Minha", b_target="NARRATOR_ROLE")], ["reordered", "narrator", "possessive", "parent_child"]),
    case(28, "Bruno é meu filho.", [relation("SON_OF", "meu filho", "Bruno", "meu", b_target="NARRATOR_ROLE")], ["direct", "narrator", "possessive", "parent_child"]),
    case(29, "Minha filha é Camila.", [relation("DAUGHTER_OF", "Minha filha", "Camila", "Minha", b_target="NARRATOR_ROLE")], ["reordered", "narrator", "possessive", "parent_child"]),
    case(30, "Renato é meu irmão.", [relation("BROTHER_OF", "meu irmão", "Renato", "meu", b_target="NARRATOR_ROLE")], ["direct", "narrator", "possessive", "sibling"]),
    case(31, "Minha irmã é Beatriz.", [relation("SISTER_OF", "Minha irmã", "Beatriz", "Minha", b_target="NARRATOR_ROLE")], ["reordered", "narrator", "possessive", "sibling"]),
    case(32, "Otávio é meu marido.", [relation("SPOUSE_OF", "meu marido", "Otávio", "meu", b_target="NARRATOR_ROLE")], ["direct", "narrator", "possessive", "spouse_surface"]),
    case(33, "Segundo Marta, Paulo é meu pai.", [relation("FATHER_OF", "meu pai", "Paulo", "meu", reporting="REPORTED", b_target="NARRATOR_ROLE")], ["reported", "narrator", "possessive", "parent_child"]),
    case(34, "Ele seria o pai de Marina?", [], ["question", "pronoun", "no_relation"]),
    case(35, "Aline disse que ela é irmã de Joana.", [relation("SISTER_OF", "irmã de", "ela", "Joana", reporting="REPORTED", a_target="UNRESOLVED_MENTION")], ["reported", "pronoun", "partial_endpoint", "sibling"]),

    case(36, "Quem é o pai de Laura?", [], ["question", "no_relation"]),
    case(37, "Será Marcos irmão de Paula?", [], ["question", "no_relation"]),
    case(38, "No relatório aparece a frase \"João é pai de Maria\".", [], ["quotation", "no_relation"]),
    case(39, "O exemplo da aula diz \"Ana é irmã de Pedro\".", [], ["quotation", "no_relation"]),
    case(40, "Encontrei o pai da Renata na praça.", [], ["incidental_kinship", "no_relation"]),
    case(41, "Lúcia conversou com a irmã do Bruno.", [], ["incidental_kinship", "no_relation"]),
    case(42, "Mauro é como um pai para a equipe.", [], ["metaphor", "no_relation"]),
    case(43, "Célia virou a mãe do projeto.", [], ["metaphor", "no_relation"]),
    case(44, "Paulo trata Renato como um irmão.", [], ["metaphor", "no_relation"]),
    case(45, "João se casou com Vera em 2018.", [], ["event_only", "no_relation"]),
    case(46, "Maria deu à luz Clara em 2002.", [], ["event_only", "no_relation"]),
    case(47, "Pedro nasceu em Recife.", [], ["event_only", "no_relation"]),
    case(48, "O segundo andar pertence a João e Maria.", [], ["reporting_negative_control", "no_relation"]),
    case(49, "Ana informou a equipe. Marcos é pai de Lúcia.", [relation("FATHER_OF", "pai de", "Marcos", "Lúcia")], ["sentence_boundary_control", "direct", "parent_child"]),
    case(50, "Uma pessoa falou sobre outra pessoa sem citar parentesco.", [], ["unknown_people", "no_relation"]),
]


if __name__ == "__main__":
    destination = Path(__file__).with_name("checkpoint_b3_unseen.jsonl")
    destination.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in CASES), encoding="utf-8")
    print(destination)
