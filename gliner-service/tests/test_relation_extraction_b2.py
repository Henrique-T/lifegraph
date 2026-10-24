"""Family-level regression tests for Checkpoint B.2 relation extraction."""

import pytest

from app.relation_extraction_b2 import extract_relations_b2, structural_relations


def candidates(text: str):
    """Run the deterministic B.2 detector and shared downstream pipeline."""
    return extract_relations_b2(text, "test", "A0_B2").candidates


@pytest.mark.parametrize(("text", "relation_type", "a", "b"), [
    ("O pai de Maria é João.", "FATHER_OF", "João", "Maria"),
    ("A mãe de Pedro é Ana.", "MOTHER_OF", "Ana", "Pedro"),
    ("O filho de Beatriz é Carlos.", "SON_OF", "Carlos", "Beatriz"),
    ("A filha de Roberto é Luiza.", "DAUGHTER_OF", "Luiza", "Roberto"),
    ("O irmão de Ana é Pedro.", "BROTHER_OF", "Pedro", "Ana"),
    ("A irmã de João é Carla.", "SISTER_OF", "Carla", "João"),
    ("O marido de Ana é João.", "SPOUSE_OF", "João", "Ana"),
    ("A esposa de Pedro é Maria.", "SPOUSE_OF", "Maria", "Pedro"),
    ("O cônjuge de Paulo é Rui.", "SPOUSE_OF", "Rui", "Paulo"),
    ("O pai dela é João.", "FATHER_OF", "João", "dela"),
])
def test_reordered_copular_family(text, relation_type, a, b):
    result = candidates(text)
    assert [(x.relation_type, x.endpoint_a_mention, x.endpoint_b_mention) for x in result] == [(relation_type, a, b)]


@pytest.mark.parametrize("text", [
    "O pai de Maria falou com João.",
    "João encontrou o pai de Maria.",
    "A irmã de Pedro telefonou para Ana.",
    "O marido de Carla chegou com Bruno.",
    "Pedro ouviu o pai de Maria no corredor.",
])
def test_reordered_negative_controls(text):
    assert candidates(text) == []


@pytest.mark.parametrize(("text", "relation_type", "a", "b"), [
    ("João, pai de Maria, chegou cedo.", "FATHER_OF", "João", "Maria"),
    ("Ana, mãe de Pedro, mora aqui.", "MOTHER_OF", "Ana", "Pedro"),
    ("Carlos, filho de Beatriz, chegou.", "SON_OF", "Carlos", "Beatriz"),
    ("Luiza, filha de Roberto, saiu.", "DAUGHTER_OF", "Luiza", "Roberto"),
    ("Tiago, irmão de Carla, voltou.", "BROTHER_OF", "Tiago", "Carla"),
    ("Ana, irmã de Pedro, mora aqui.", "SISTER_OF", "Ana", "Pedro"),
    ("Carla, esposa de João, falou comigo.", "SPOUSE_OF", "Carla", "João"),
    ("Rafael, marido de Sônia, telefonou.", "SPOUSE_OF", "Rafael", "Sônia"),
    ("Paulo falou com Pedro, pai de Maria, ontem.", "FATHER_OF", "Pedro", "Maria"),
    ("Clara viu Ana, irmã de Bruno, na praça.", "SISTER_OF", "Ana", "Bruno"),
])
def test_apposition_attaches_to_local_head(text, relation_type, a, b):
    result = candidates(text)
    assert any((x.relation_type, x.endpoint_a_mention, x.endpoint_b_mention) == (relation_type, a, b) for x in result)


@pytest.mark.parametrize(("text", "surface"), [
    ("João é pai da Maria.", "pai da"), ("Ana é mãe do Pedro.", "mãe do"),
    ("Luiza é filha do Roberto.", "filha do"), ("Tiago é irmão da Carla.", "irmão da"),
    ("Helena é irmã do Marcos.", "irmã do"), ("Carla é esposa do João.", "esposa do"),
    ("Rafael é marido da Sônia.", "marido da"), ("Ana é cônjuge do Pedro.", "cônjuge do"),
])
def test_contracted_prepositions(text, surface):
    assert candidates(text)[0].relation_surface_text == surface


@pytest.mark.parametrize(("text", "relation_type", "a", "b"), [
    ("Maria tem João como pai.", "FATHER_OF", "João", "Maria"),
    ("Pedro tem Ana como mãe.", "MOTHER_OF", "Ana", "Pedro"),
    ("Beatriz tem Carlos como filho.", "SON_OF", "Carlos", "Beatriz"),
    ("João tem Ana como filha.", "DAUGHTER_OF", "Ana", "João"),
    ("Carla tem Tiago como irmão.", "BROTHER_OF", "Tiago", "Carla"),
    ("Pedro tem Carla como irmã.", "SISTER_OF", "Carla", "Pedro"),
    ("Maria tem João como marido.", "SPOUSE_OF", "João", "Maria"),
    ("João tem Maria como esposa.", "SPOUSE_OF", "Maria", "João"),
    ("Paulo tem Rui como cônjuge.", "SPOUSE_OF", "Rui", "Paulo"),
    ("Sônia tem Rafael como marido.", "SPOUSE_OF", "Rafael", "Sônia"),
])
def test_ter_como_direction_is_role_then_holder(text, relation_type, a, b):
    item = candidates(text)[0]
    assert (item.relation_type, item.endpoint_a_mention, item.endpoint_b_mention) == (relation_type, a, b)


@pytest.mark.parametrize("text", [
    "Maria trata João como um pai.", "João tem Pedro como um irmão.",
    "Ana considera Carla como uma irmã.", "Pedro vê João como um filho.",
])
def test_social_comparison_is_not_ter_como_relation(text):
    assert candidates(text) == []


@pytest.mark.parametrize("text", [
    "João é, segundo o registro familiar, pai de Maria.",
    "Ana é, segundo ela própria, irmã de Pedro.",
    "Carla é, segundo os documentos da família, esposa de João.",
    "Tiago é, segundo o registro familiar, irmão de Carla.",
    "Luiza é, segundo ela própria, filha de Roberto.",
    "Carlos é, segundo os documentos da família, filho de Beatriz.",
    "Ana é, segundo o registro familiar, mãe de Pedro.",
    "Rafael é, segundo ela própria, marido de Sônia.",
])
def test_allowlisted_discontinuous_modifiers(text):
    assert len(candidates(text)) == 1


@pytest.mark.parametrize("text", [
    "João é, conforme alguém talvez tenha dito, pai de Maria.",
    "Ana é, se Pedro estiver certo, irmã de Carla.",
    "João é, apesar de negar isso, pai de Maria.",
])
def test_unapproved_discontinuous_modifiers_abstain(text):
    assert candidates(text) == []


def test_appositive_chain_keeps_independent_objects():
    result = candidates("João, pai de Maria e irmão de Pedro, chegou.")
    assert {(x.relation_type, x.endpoint_a_mention, x.endpoint_b_mention) for x in result} == {
        ("FATHER_OF", "João", "Maria"), ("BROTHER_OF", "João", "Pedro")
    }


@pytest.mark.parametrize("prefix", [
    "De jeito nenhum", "De forma alguma", "Em hipótese alguma",
])
def test_emphatic_negation(prefix):
    assert candidates(f"{prefix} João é pai de Maria.")[0].polarity == "NEGATED"


@pytest.mark.parametrize("text", [
    "João nunca foi pai de Maria.", "João jamais foi pai de Maria.",
    "Pedro disse que João não é pai de Maria.",
    "Pedro disse que de jeito nenhum João é pai de Maria.",
    "Pedro afirmou que João jamais foi pai de Maria.",
    "Ana negou que João seja pai de Maria.",
    "De forma alguma Ana é irmã de Pedro.",
])
def test_negation_composes_with_reporting(text):
    item = candidates(text)[0]
    assert item.polarity == "NEGATED"
    if "disse" in text or "afirmou" in text or "negou" in text:
        assert item.reporting_mode == "REPORTED"


@pytest.mark.parametrize("prefix", [
    "Parece que", "É possível que", "Pode ser que", "Talvez", "Acho que",
    "Acredito que", "Não tenho certeza se", "Há dúvida se", "Não se sabe se",
    "Tudo indica, sem certeza, que",
])
def test_uncertainty_family(prefix):
    assert candidates(f"{prefix} João seja pai de Maria.")[0].epistemic_status == "UNCERTAIN"


@pytest.mark.parametrize("text", [
    "Se João fosse pai de Maria, saberia disso.",
    "Caso João fosse pai de Maria, haveria registro.",
    "João seria pai de Maria se o relato estivesse correto.",
])
def test_hypothetical_scope(text):
    assert candidates(text)[0].epistemic_status == "HYPOTHETICAL"


def test_reported_dimensions_remain_independent():
    negated = candidates("Pedro afirmou que João jamais foi pai de Maria.")[0]
    uncertain = candidates("Pedro disse que talvez João seja pai de Maria.")[0]
    assert (negated.polarity, negated.epistemic_status, negated.reporting_mode, negated.temporal_scope) == (
        "NEGATED", "ASSERTED", "REPORTED", "PAST")
    assert (uncertain.polarity, uncertain.epistemic_status, uncertain.reporting_mode) == (
        "POSITIVE", "UNCERTAIN", "REPORTED")


@pytest.mark.parametrize("text", [
    "Pedro disse a Carlos que o pai de Maria é João.",
    "Renata contou a Bruno que a irmã de Ana é Carla.",
    "Paulo explicou a Rui que o marido de Sônia é Rafael.",
    "Clara disse a Ana que a mãe de Pedro é Beatriz.",
    "Carlos contou a João que a filha de Roberto é Luiza.",
    "Maria explicou a Pedro que o irmão de Carla é Tiago.",
    "Bruno afirmou a Renata que a esposa de João é Carla.",
    "Paulo declarou a Ana que o cônjuge de Rui é Marcos.",
    "Pedro contou a João que o filho de Beatriz é Carlos.",
    "Ana explicou a Carla que o pai de Maria é João.",
])
def test_reporting_distractors_do_not_become_endpoints(text):
    item = candidates(text)[0]
    assert item.reporting_source_mention not in {item.endpoint_a_mention, item.endpoint_b_mention}


@pytest.mark.parametrize("text", [
    "O pai dela é João.", "A mãe dele é Ana.", "O irmão dela é Pedro.", "A irmã dele é Carla.",
    "A esposa dele é Maria.", "O marido dela é João.", "Ela é mãe de Pedro.", "Ele é pai de Maria.",
])
def test_pronouns_remain_unresolved(text):
    item = candidates(text)[0]
    assert "UNRESOLVED_MENTION" in {item.endpoint_a_resolution_state, item.endpoint_b_resolution_state}


@pytest.mark.parametrize("text", [
    "João falou com o pai de Maria.", "Ana encontrou a irmã de Pedro.",
    "O manual cita \"João é pai de Maria\".", "João é como um irmão para Maria.",
    "Maria trata João como um pai.", "João se casou com Maria em 2019.",
    "Ana deu à luz Pedro em 2001.", "Pedro chamou Ana de irmã.",
    "João trabalha com o marido de Carla.", "Maria faz papel de mãe no projeto.",
])
def test_new_syntax_negative_controls(text):
    assert candidates(text) == []
