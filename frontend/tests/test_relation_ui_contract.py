"""Static C3 UI contract checks without adding a second JS dependency stack."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PANEL = (ROOT / "src/components/RelationReviewPanel.tsx").read_text(encoding="utf-8")
GRAPH = (ROOT / "src/components/GraphView.tsx").read_text(encoding="utf-8")
CLIENT = (ROOT / "src/api/client.ts").read_text(encoding="utf-8")
TYPES = (ROOT / "src/api/types.ts").read_text(encoding="utf-8")
APP = (ROOT / "src/App.tsx").read_text(encoding="utf-8")


def test_relation_extraction_client():
    assert '"/relation-extractions"' in CLIENT


def test_review_get_client():
    assert "getRelationReview" in CLIENT


def test_accept_reject_persist_clients():
    assert "/accept`" in CLIENT and "/reject`" in CLIENT and "/persist`" in CLIENT


def test_persist_command_has_no_semantic_payload():
    persist = CLIENT.split("export const persistRelationCandidate", 1)[1]
    assert 'body: "{}"' in persist
    assert "relation_type" not in persist


def test_explicit_two_person_selectors():
    assert "Endpoint A — Pessoa LifeGraph" in PANEL
    assert "Endpoint B — Pessoa LifeGraph" in PANEL
    assert PANEL.count("Selecione explicitamente…") == 2


def test_no_person_auto_binding():
    assert "autoSelect" not in PANEL and "fuzzy" not in PANEL


def test_narrator_warning_and_no_autobind():
    assert "NARRATOR_ROLE" in PANEL
    assert "nenhuma identidade é presumida" in PANEL


def test_question_is_visible_and_not_directly_persistible():
    assert "Relação mencionada em uma pergunta" in PANEL
    assert 'item.review_status === "ACCEPTED_FOR_PERSISTENCE" && item.eligible' in PANEL


def test_server_blocker_is_rendered():
    assert "item.primary_blocker" in PANEL
    assert "NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS" in PANEL


def test_immutable_dimensions_have_no_inputs():
    for field in ("polarity", "epistemic_status", "reporting_mode", "temporal_scope", "origin", "verification_status"):
        assert f'name="{field}"' not in PANEL


def test_declared_claim_language():
    assert "Ainda não é um fato confirmado" in PANEL
    assert 'setMessage("DECLARADO oficialmente")' in PANEL


def test_relation_claim_graph_type():
    assert '"RelationClaim"' in TYPES and 'node.type === "RelationClaim"' in GRAPH


def test_graph_has_role_specific_edges():
    assert '"ENDPOINT_A"' in GRAPH and '"ENDPOINT_B"' in GRAPH and '"EXTRACTED_FROM"' in GRAPH


def test_graph_does_not_create_direct_kinship_edges():
    for edge in ("FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF", "BROTHER_OF", "SISTER_OF", "SPOUSE_OF"):
        assert f'relatedNode(visibleGraph, selected.id, "{edge}"' not in GRAPH


def test_relation_claim_provenance_fields():
    for field in ("review_id", "candidate_id", "pipeline_id", "configuration_hash", "canonical_pair_key", "original_relation_surface", "accepted_relation_surface"):
        assert field in GRAPH


def test_event_and_relation_surfaces_are_separate():
    assert "<CandidateCard" in APP and "<RelationReviewPanel" in APP
    assert "RELAÇÃO · interpretação automática" in PANEL


def test_multiple_candidates_render_independently():
    assert "review.candidates.map" in PANEL and "key={item.candidate_id}" in PANEL


def test_rejected_state_is_terminal_in_ui():
    assert 'item.review_status === "REJECTED"' in PANEL
    assert "disabled={terminal || Boolean(busy)}" in PANEL


def test_expiration_message_requires_new_extraction():
    assert "Esta revisão expirou. Execute a extração novamente." in CLIENT


def test_persistence_success_hides_technical_replay_and_uuid_details():
    assert "result.idempotent_replay" not in PANEL
    assert 'setMessage("DECLARADO oficialmente")' in PANEL
    assert 'setMessage(`' not in PANEL


def test_graph_does_not_collapse_canonical_pairs():
    assert "canonical_pair_key" in GRAPH
    assert ".filter((node) => node.type === \"ClaimEvent\" || node.type === \"RelationClaim\")" in GRAPH
    assert "new Map" not in GRAPH.split("const claims =", 1)[1].split(";", 1)[0]


def test_action_loading_states_are_visible():
    assert "Extraindo eventos e relações…" in APP
    for label in ("Aceitando…", "Rejeitando…", "Persistindo…"):
        assert label in PANEL


def test_advanced_relation_correction_controls_are_hidden_in_simplified_ui():
    for label in ("Tipo aceito", "Evidência da relação", "Menção do endpoint A", "Menção do endpoint B", "Trocar papéis A/B"):
        assert label not in PANEL
    assert "corrections: {}" in PANEL


def test_origin_and_verification_are_not_sent_by_acceptance():
    accept_body = PANEL.split("acceptRelationCandidate", 2)[2].split("});", 1)[0]
    assert "origin" not in accept_body and "verification_status" not in accept_body


def test_graph_relation_claim_has_text_and_shape_distinction():
    assert "RelationClaim\\n" in GRAPH
    assert 'node[type = "RelationClaim"]' in GRAPH


def test_single_narrative_submission_starts_both_specialized_extractions():
    assert "Promise.all([extractNarrative(text.trim()), extractRelations(text.trim())])" in APP
    assert "Eventos civis extraídos" in APP
    assert "Relações familiares extraídas" in PANEL


def test_progressive_review_and_graph_stages_are_distinct():
    assert 'type WorkflowStage = "narrative" | "review" | "graph" | "complete"' in APP
    assert 'setWorkflowStage("review")' in APP
    assert 'setWorkflowStage("graph")' in APP


def test_independent_graph_consultation_is_always_available():
    assert "always-available-graph" in APP
    assert 'variant="explorer"' in APP
    assert "independentemente da narrativa atual" in APP


def test_person_search_filters_but_does_not_bind_until_explicit_selection():
    change = GRAPH.split("onChange={(event) => {", 1)[1].split("}}", 1)[0]
    assert "setExplorerPersonSearch(event.target.value)" in change
    assert 'setExplorerPersonId("")' in change
    option = GRAPH.split('role="option"', 1)[1].split("}}>", 1)[0]
    assert "setExplorerPersonId(person.id)" in option


def test_timeline_is_person_scoped_and_chronologically_ordered():
    assert "timelineSubgraph(graph, explorerPersonId)" in GRAPH
    assert 'node.type !== "RelationClaim"' in GRAPH
    assert 'node.type !== "Person" || node.id === personId' in GRAPH
    assert ".sort((left, right) => Date.parse(left) - Date.parse(right))" in GRAPH


def test_graph_timeline_switching_is_local_view_state_only():
    assert 'setViewMode("focus")' in GRAPH
    assert 'setViewMode("timeline")' in GRAPH
    switching = "\n".join(line for line in GRAPH.splitlines() if "setViewMode" in line)
    for mutation in ("accept", "persist", "reconcile", "fetch("):
        assert mutation not in switching.lower()
