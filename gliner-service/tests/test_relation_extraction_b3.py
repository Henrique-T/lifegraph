"""Checkpoint B.3 regression tests for reporting and narrator endpoints."""

import pytest

from app.relation_extraction_b2 import PIPELINE_ID, extract_relations_b2


def candidate(text: str):
    result = extract_relations_b2(text, "B3-TEST", "A0_B2")
    assert len(result.candidates) == 1
    return result.candidates[0]


@pytest.mark.parametrize("verb", [
    "disse", "afirmou", "contou", "explicou", "declarou", "relatou",
    "informou", "comunicou", "perguntou", "negou",
])
def test_reporting_verb_families(verb):
    item = candidate(f"Pedro {verb} que João é pai de Maria.")
    assert item.reporting_mode == "REPORTED"
    assert item.reporting_source_mention == "Pedro"


@pytest.mark.parametrize("prefix,source", [
    ("Segundo Pedro,", "Pedro"),
    ("Segundo Ana,", "Ana"),
    ("Segundo Carla,", "Carla"),
    ("Segundo Renato,", "Renato"),
    ("De acordo com Pedro,", "Pedro"),
    ("De acordo com Ana,", "Ana"),
    ("De acordo com Carla,", "Carla"),
    ("De acordo com Renato,", "Renato"),
])
def test_source_introduction_families(prefix, source):
    item = candidate(f"{prefix} João é pai de Maria.")
    assert item.reporting_mode == "REPORTED"
    assert item.reporting_source_mention == source


@pytest.mark.parametrize("marker", [
    "talvez", "acho que", "acredito que", "parece que",
    "é possível que", "pode ser que", "não tenho certeza se", "sem certeza",
])
def test_reported_uncertainty_is_compositional(marker):
    item = candidate(f"Pedro disse que {marker} João seja pai de Maria.")
    assert (item.reporting_mode, item.epistemic_status) == ("REPORTED", "UNCERTAIN")


@pytest.mark.parametrize("text", [
    "Pedro afirmou que João não é pai de Maria.",
    "Pedro afirmou que João nunca foi pai de Maria.",
    "Pedro afirmou que João jamais foi pai de Maria.",
    "Pedro afirmou que de jeito nenhum João é pai de Maria.",
    "Pedro afirmou que de forma alguma João é pai de Maria.",
    "Pedro afirmou que em hipótese alguma João é pai de Maria.",
    "Pedro afirmou que João não era pai de Maria.",
    "Pedro afirmou que João não foi pai de Maria.",
])
def test_reported_negation_is_compositional(text):
    item = candidate(text)
    assert (item.reporting_mode, item.polarity) == ("REPORTED", "NEGATED")


@pytest.mark.parametrize("copula", ["foi", "era", "foram", "eram", "foi", "era"])
def test_reported_past_is_compositional(copula):
    text = f"Pedro declarou que João {copula} marido de Maria."
    item = candidate(text)
    assert (item.reporting_mode, item.temporal_scope) == ("REPORTED", "PAST")


@pytest.mark.parametrize("text", [
    "Pedro disse algo. João é pai de Maria.",
    "Maria contou uma história. João é pai de Pedro.",
    "Pedro afirmou sua opinião; João é pai de Maria.",
    "Ana relatou o ocorrido. Carla é mãe de João.",
    "Segundo andar, João é pai de Maria.",
    "João disse algo antes. Carlos é pai de Maria.",
    "Pedro informou a equipe. João é irmão de Carlos.",
    "Maria explicou o problema. Ana é irmã de João.",
    "Pedro declarou seu voto. João é filho de Maria.",
    "Ana contou até três. Maria é filha de João.",
])
def test_reporting_does_not_cross_sentence_or_clause_boundaries(text):
    assert candidate(text).reporting_mode == "DIRECT"


@pytest.mark.parametrize("text,relation_type,name,possessive", [
    ("João é meu pai.", "FATHER_OF", "João", "meu"),
    ("Ana é minha mãe.", "MOTHER_OF", "Ana", "minha"),
    ("Pedro é meu filho.", "SON_OF", "Pedro", "meu"),
    ("Carla é minha filha.", "DAUGHTER_OF", "Carla", "minha"),
    ("João é meu irmão.", "BROTHER_OF", "João", "meu"),
    ("Maria é minha irmã.", "SISTER_OF", "Maria", "minha"),
    ("Pedro é meu marido.", "SPOUSE_OF", "Pedro", "meu"),
    ("Maria é minha esposa.", "SPOUSE_OF", "Maria", "minha"),
])
def test_narrator_relative_predicates(text, relation_type, name, possessive):
    item = candidate(text)
    assert item.relation_type == relation_type
    assert item.endpoint_a_mention == name
    assert item.endpoint_a_semantic_target == "EXPLICIT_MENTION"
    assert item.endpoint_b_mention == possessive
    assert item.endpoint_b_semantic_target == "NARRATOR_ROLE"
    assert not hasattr(item, "endpoint_b_person_id")


def test_compound_name_is_preserved_for_narrator_relation():
    text = "Nasci em 1988, casei em 2010 e me casei novamente em 2019. Antonella Moraes é minha filha."
    item = candidate(text)
    assert item.relation_type == "DAUGHTER_OF"
    assert item.endpoint_a_mention == "Antonella Moraes"
    assert text[item.endpoint_a_span_start:item.endpoint_a_span_end] == "Antonella Moraes"
    assert item.endpoint_b_mention == "minha"
    assert item.endpoint_b_semantic_target == "NARRATOR_ROLE"


@pytest.mark.parametrize("text,relation_type,name,possessive", [
    ("Meu pai é João.", "FATHER_OF", "João", "Meu"),
    ("Minha mãe é Ana.", "MOTHER_OF", "Ana", "Minha"),
    ("Meu filho é Pedro.", "SON_OF", "Pedro", "Meu"),
    ("Minha filha é Carla.", "DAUGHTER_OF", "Carla", "Minha"),
    ("Meu irmão é João.", "BROTHER_OF", "João", "Meu"),
    ("Minha irmã é Maria.", "SISTER_OF", "Maria", "Minha"),
    ("Meu marido é Pedro.", "SPOUSE_OF", "Pedro", "Meu"),
    ("Minha esposa é Maria.", "SPOUSE_OF", "Maria", "Minha"),
])
def test_reordered_narrator_relative_predicates(text, relation_type, name, possessive):
    item = candidate(text)
    assert (item.relation_type, item.endpoint_a_mention) == (relation_type, name)
    assert (item.endpoint_b_mention, item.endpoint_b_semantic_target) == (possessive, "NARRATOR_ROLE")


@pytest.mark.parametrize("text,attribute,value", [
    ("Pedro disse que João é meu pai.", "reporting_mode", "REPORTED"),
    ("João não é meu pai.", "polarity", "NEGATED"),
    ("Talvez João seja meu pai.", "epistemic_status", "UNCERTAIN"),
    ("Pedro foi meu marido.", "temporal_scope", "PAST"),
    ("Ana afirmou que talvez Maria seja minha irmã.", "reporting_mode", "REPORTED"),
])
def test_narrator_role_composes_with_guards(text, attribute, value):
    item = candidate(text)
    assert getattr(item, attribute) == value
    assert item.endpoint_b_semantic_target == "NARRATOR_ROLE"


def test_coordinated_reporting_predicate_is_reported_without_resolving_pronoun():
    item = candidate("Paulo encontrou Renato e disse que ele é pai de Maria.")
    assert item.reporting_mode == "REPORTED"
    assert item.endpoint_a_semantic_target == "UNRESOLVED_MENTION"
    assert item.endpoint_a_resolution_state == "UNRESOLVED_MENTION"


def test_pipeline_is_frozen_without_graph_identity_fields():
    item = candidate("João é meu pai.")
    assert PIPELINE_ID == "LIFEGRAPH_PERSON_RELATION_V1"
    assert item.pipeline_id == PIPELINE_ID
    assert not any("person_id" in name for name in type(item).model_fields)
