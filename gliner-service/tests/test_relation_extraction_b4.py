"""Checkpoint B.4 tests for relative apposition and interrogatives."""

import pytest

from app.relation_extraction_b2 import extract_relations_b2


def extract(text):
    return extract_relations_b2(text, "B4-TEST", "A0_B2")


def one(text):
    result = extract(text)
    assert len(result.candidates) == 1
    return result.candidates[0]


@pytest.mark.parametrize("text,kind,a,b", [
    ("Rafael, que é pai de Luana, mora aqui.", "FATHER_OF", "Rafael", "Luana"),
    ("Clara, que é mãe de Davi, chegou.", "MOTHER_OF", "Clara", "Davi"),
    ("Breno, que é filho de Marta, telefonou.", "SON_OF", "Breno", "Marta"),
    ("Lia, que é filha de Caio, sorriu.", "DAUGHTER_OF", "Lia", "Caio"),
    ("Ivo, que é irmão de Sara, viajou.", "BROTHER_OF", "Ivo", "Sara"),
    ("Eva, que é irmã de Rui, voltou.", "SISTER_OF", "Eva", "Rui"),
    ("Otávio, que é marido de Alice, saiu.", "SPOUSE_OF", "Otávio", "Alice"),
    ("Alice, que é esposa de Otávio, saiu.", "SPOUSE_OF", "Alice", "Otávio"),
    ("Marcos, que é pai da Lúcia, mora aqui.", "FATHER_OF", "Marcos", "Lúcia"),
    ("Helena, que é mãe do Caio, chegou.", "MOTHER_OF", "Helena", "Caio"),
])
def test_relative_apposition_basic(text, kind, a, b):
    item = one(text)
    assert (item.relation_type, item.endpoint_a_mention, item.endpoint_b_mention) == (kind, a, b)


@pytest.mark.parametrize("text,field,value", [
    ("João, que não é pai de Maria, chegou.", "polarity", "NEGATED"),
    ("Bianca, que nunca foi mãe de Davi, respondeu.", "polarity", "NEGATED"),
    ("Paulo, que jamais foi filho de Ana, saiu.", "polarity", "NEGATED"),
    ("Marina, que talvez seja irmã de Paula, chegou.", "epistemic_status", "UNCERTAIN"),
    ("João, que foi marido de Ana, mudou-se.", "temporal_scope", "PAST"),
    ("Ana, que era esposa de Pedro, viajou.", "temporal_scope", "PAST"),
    ("Carlos, que talvez seja irmão do Rui, ligou.", "epistemic_status", "UNCERTAIN"),
    ("Lia, que não é filha do Mauro, respondeu.", "polarity", "NEGATED"),
])
def test_relative_apposition_composes_with_guards(text, field, value):
    assert getattr(one(text), field) == value


@pytest.mark.parametrize("text,a,b,source", [
    ("João, que disse que Pedro é pai de Maria, chegou.", "Pedro", "Maria", "João"),
    ("Clara, que afirmou que Ana é mãe de Rui, saiu.", "Ana", "Rui", "Clara"),
    ("Breno, que contou que Ivo é irmão de Sara, voltou.", "Ivo", "Sara", "Breno"),
    ("Lia, que declarou que Eva é irmã de Caio, falou.", "Eva", "Caio", "Lia"),
    ("Marta, que relatou que Raul foi marido de Rosa, chegou.", "Raul", "Rosa", "Marta"),
    ("Nina, que informou que Bia é filha de Hugo, saiu.", "Bia", "Hugo", "Nina"),
])
def test_nested_reporting_uses_inner_subject(text, a, b, source):
    item = one(text)
    assert (item.endpoint_a_mention, item.endpoint_b_mention) == (a, b)
    assert (item.reporting_mode, item.reporting_source_mention) == ("REPORTED", source)


@pytest.mark.parametrize("text,kind,name,possessive", [
    ("João, que é meu pai, chegou.", "FATHER_OF", "João", "meu"),
    ("Ana, que é minha mãe, chegou.", "MOTHER_OF", "Ana", "minha"),
    ("Pedro, que é meu filho, chegou.", "SON_OF", "Pedro", "meu"),
    ("Carla, que é minha filha, chegou.", "DAUGHTER_OF", "Carla", "minha"),
    ("Rui, que é meu irmão, chegou.", "BROTHER_OF", "Rui", "meu"),
    ("Eva, que é minha esposa, chegou.", "SPOUSE_OF", "Eva", "minha"),
])
def test_relative_narrator_role(text, kind, name, possessive):
    item = one(text)
    assert (item.relation_type, item.endpoint_a_mention) == (kind, name)
    assert (item.endpoint_b_mention, item.endpoint_b_semantic_target) == (possessive, "NARRATOR_ROLE")
    assert not any("person_id" in field for field in type(item).model_fields)


@pytest.mark.parametrize("text", [
    "João, que conhece o pai de Maria, chegou.",
    "João, que falou com o pai de Maria, chegou.",
    "João, que trabalha como pai social no projeto, chegou.",
    "João quebrou o objeto que Maria trouxe.",
    "João, que visitou a mãe de Pedro, saiu.",
    "Clara, que encontrou a irmã de Ana, voltou.",
    "Rui, que conversou com o marido de Bia, ligou.",
    "Marta, que escreveu sobre o filho de Ana, saiu.",
    "João, que conhece Pedro, pai de Maria, chegou.",
    "Ana, que viu Carla, irmã de Rui, saiu.",
])
def test_relative_negative_and_ambiguous_controls_abstain(text):
    assert extract(text).candidates == []


@pytest.mark.parametrize("name,term,other,kind", [
    ("João", "pai", "Maria", "FATHER_OF"),
    ("Ana", "mãe", "Pedro", "MOTHER_OF"),
    ("Rui", "filho", "Clara", "SON_OF"),
    ("Bia", "filha", "Caio", "DAUGHTER_OF"),
    ("Ivo", "irmão", "Sara", "BROTHER_OF"),
    ("Eva", "irmã", "Hugo", "SISTER_OF"),
    ("Raul", "marido", "Rosa", "SPOUSE_OF"),
    ("Rosa", "esposa", "Raul", "SPOUSE_OF"),
])
def test_yes_no_questions_are_candidates_but_blocked(name, term, other, kind):
    item = one(f"{name} é {term} de {other}?")
    assert item.relation_type == kind
    assert item.epistemic_status == "UNCERTAIN"
    assert item.persistence_eligibility == "NOT_PERSISTIBLE_UNCERTAIN"


@pytest.mark.parametrize("term,other,kind", [
    ("pai", "Maria", "FATHER_OF"), ("mãe", "Pedro", "MOTHER_OF"),
    ("filho", "Ana", "SON_OF"), ("filha", "Caio", "DAUGHTER_OF"),
    ("irmão", "Sara", "BROTHER_OF"), ("esposa", "Rui", "SPOUSE_OF"),
])
def test_wh_questions_preserve_unresolved_endpoint(term, other, kind):
    item = one(f"Quem é o {term} de {other}?")
    assert item.relation_type == kind
    assert item.endpoint_a_mention == "Quem"
    assert item.endpoint_a_semantic_target == "UNRESOLVED_MENTION"
    assert item.persistence_eligibility == "NOT_PERSISTIBLE_UNCERTAIN"


@pytest.mark.parametrize("text", [
    "Será que João é pai de Maria?", "Talvez Ana seja mãe de Pedro?",
    "Pode ser que Rui seja filho de Clara?", "É possível que Bia seja filha de Caio?",
    "Será que Ivo é irmão de Sara?", "Talvez Eva seja esposa de Hugo?",
])
def test_modal_questions_are_uncertain(text):
    assert one(text).epistemic_status == "UNCERTAIN"


@pytest.mark.parametrize("text", [
    "Pedro perguntou se João é pai de Maria?", "Ana perguntou se Clara é mãe de Rui?",
    "Bia perguntou se Ivo é filho de Sara?", "Caio perguntou se Eva é filha de Hugo?",
    "Lia perguntou se Rui é irmão de Ana?", "Marta perguntou se Raul é marido de Rosa?",
])
def test_reported_questions_are_reported_and_blocked(text):
    item = one(text)
    assert (item.reporting_mode, item.epistemic_status) == ("REPORTED", "UNCERTAIN")
    assert item.persistence_eligibility != "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED"


@pytest.mark.parametrize("text", [
    "João não é pai de Maria?", "Ana nunca foi mãe de Pedro?",
    "Rui jamais foi filho de Clara?", "Bia não é filha de Caio?",
    "Ivo não é irmão de Sara?", "Eva não é esposa de Hugo?",
])
def test_negated_questions_compose_without_becoming_facts(text):
    item = one(text)
    assert (item.polarity, item.epistemic_status) == ("NEGATED", "UNCERTAIN")
    assert item.persistence_eligibility == "NOT_PERSISTIBLE_NEGATED"


@pytest.mark.parametrize("text", [
    "João perguntou sobre o pai de Maria?", "Ana falou sobre a mãe de Pedro?",
    "Rui encontrou o filho de Clara?", "Bia viu a filha de Caio?",
    "Ivo conversou com o irmão de Sara?", "Eva telefonou para a irmã de Hugo?",
    "Marta encontrou o marido de Rosa?", "Raul conhece a esposa de Lia?",
])
def test_incidental_question_controls_do_not_emit_relations(text):
    assert extract(text).candidates == []


def test_focused_question_preserves_direction_and_is_blocked():
    item = one("É João o pai de Maria?")
    assert (item.endpoint_a_mention, item.endpoint_b_mention) == ("João", "Maria")
    assert item.persistence_eligibility == "NOT_PERSISTIBLE_UNCERTAIN"


@pytest.mark.parametrize("text,kind", [
    ("Rafael, que não é pai de Luana, saiu cedo.", "FATHER_OF"),
    ("Bianca, que jamais foi mãe de Davi, respondeu.", "MOTHER_OF"),
])
def test_b3_relative_failures_are_permanent_regressions(text, kind):
    assert one(text).relation_type == kind


@pytest.mark.parametrize("text", ["Ele seria o pai de Marina?", "Quem é o pai de Laura?"])
def test_b3_questions_are_blocked_relation_mentions(text):
    item = one(text)
    assert item.epistemic_status == "UNCERTAIN"
    assert item.persistence_eligibility != "LINGUISTICALLY_ELIGIBLE_REVIEW_AND_BINDING_REQUIRED"
