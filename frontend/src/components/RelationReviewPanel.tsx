import { useState } from "react";
import { acceptRelationCandidate, friendlyError, persistRelationCandidate, rejectRelationCandidate } from "../api/client";
import type { Person, RelationReviewItem, RelationReviewSession, RelationType } from "../api/types";

const relationLabels: Record<RelationType, string> = {
  FATHER_OF: "pai de", MOTHER_OF: "mãe de", SON_OF: "filho de", DAUGHTER_OF: "filha de",
  BROTHER_OF: "irmão de", SISTER_OF: "irmã de", SPOUSE_OF: "cônjuge de",
};
const blockerLabels: Record<string, string> = {
  PERSISTIBLE: "Elegível para persistência.",
  NOT_PERSISTIBLE_NEGATED: "A relação está negada na narrativa.",
  NOT_PERSISTIBLE_UNCERTAIN: "A narrativa expressa incerteza ou uma pergunta.",
  NOT_PERSISTIBLE_HYPOTHETICAL: "A relação é hipotética.",
  NOT_PERSISTIBLE_REPORTED: "A relação foi relatada por outra pessoa.",
  NOT_PERSISTIBLE_PARTIAL_ENDPOINT: "Um endpoint linguístico está incompleto.",
  NOT_PERSISTIBLE_UNSUPPORTED_TEMPORAL_SCOPE: "Relações históricas ou temporais não resolvidas não podem ser persistidas nesta versão.",
  NOT_PERSISTIBLE_UNBOUND_ENDPOINT: "Selecione explicitamente as duas pessoas.",
  NOT_PERSISTIBLE_SAME_PERSON_ENDPOINTS: "Os dois endpoints não podem apontar para a mesma pessoa.",
  NOT_PERSISTIBLE_UNGROUNDED_CORRECTION: "A correção deve corresponder exatamente a um trecho da narrativa.",
  NOT_PERSISTIBLE_NOT_ACCEPTED: "A declaração ainda não foi aceita pelo revisor.",
};

interface Props { people: Person[]; review: RelationReviewSession; onReviewChange: (review: RelationReviewSession) => void; onGraphRefresh: () => Promise<void>; onPersonFocus: (personIds: string[]) => void; embedded?: boolean }

const polarityLabels = { POSITIVE: "afirmativa", NEGATED: "negada" } as const;
const epistemicLabels = { ASSERTED: "afirmada", UNCERTAIN: "incerta", HYPOTHETICAL: "hipotética" } as const;
const reportingLabels = { DIRECT: "direta", REPORTED: "relatada por outra pessoa" } as const;
const temporalLabels = { CURRENT_OR_UNSPECIFIED: "atual ou sem período informado", PAST: "passada", UNRESOLVED: "período não resolvido" } as const;

function RelationCard({ item, people, onUpdate, onGraphRefresh, onPersonFocus }: { item: RelationReviewItem; people: Person[]; onUpdate: (item: RelationReviewItem) => void; onGraphRefresh: () => Promise<void>; onPersonFocus: (ids: string[]) => void }) {
  const candidate = item.corrected_candidate ?? item.original_candidate;
  const [personA, setPersonA] = useState(item.endpoint_a_person?.person_id ?? "");
  const [personB, setPersonB] = useState(item.endpoint_b_person?.person_id ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const question = item.source_text.trim().endsWith("?");
  const terminal = item.review_status === "REJECTED" || item.persistence_status === "PERSISTED";

  async function accept() {
    setBusy("accept"); setMessage(null);
    try {
      const result = await acceptRelationCandidate(item.review_id, item.candidate_id, { endpoint_a_person_id: personA || null, endpoint_b_person_id: personB || null, reviewer_accepted: true, corrections: {} });
      onUpdate(result.item); setMessage(result.eligible ? "ELIGÍVEL para persistência. Ainda não é um fato confirmado." : blockerLabels[result.primary_blocker] ?? result.primary_blocker);
    } catch (error) { setMessage(friendlyError(error)); } finally { setBusy(null); }
  }
  async function reject() {
    setBusy("reject"); setMessage(null);
    try { onUpdate((await rejectRelationCandidate(item.review_id, item.candidate_id)).item); setMessage("Relação rejeitada; nenhuma escrita no grafo foi realizada."); }
    catch (error) { setMessage(friendlyError(error)); } finally { setBusy(null); }
  }
  async function persist() {
    setBusy("persist"); setMessage(null);
    try {
      const result = await persistRelationCandidate(item.review_id, item.candidate_id);
      onUpdate({ ...item, persistence_status: "PERSISTED", relation_claim_id: result.relation_claim_id, persisted_at: result.persisted_at });
      setMessage("DECLARADO oficialmente");
      await onGraphRefresh();
    } catch (error) { setMessage(friendlyError(error)); } finally { setBusy(null); }
  }

  return <article className="candidate relation-candidate" aria-label={`Relação ${candidate.relation_type}`}>
    <header className="candidate-header"><div><span className="candidate-kind relation-kind">RELAÇÃO · interpretação automática</span><h3>{relationLabels[candidate.relation_type]}</h3></div><span className={`status ${item.eligible ? "accepted" : "unresolved"}`}>{item.persistence_status === "PERSISTED" ? "DECLARADO" : item.review_status}</span></header>
    <blockquote className="source-narrative">{item.source_text}</blockquote>
    <dl className="candidate-facts">
      <div><dt>Evidência</dt><dd>“{candidate.relation_surface_text}”</dd></div><div><dt>Pessoa A</dt><dd>{candidate.endpoint_a_mention ?? "não resolvida"}</dd></div>
      <div><dt>Pessoa B</dt><dd>{candidate.endpoint_b_mention ?? "não resolvida"}</dd></div><div><dt>Como aparece no texto</dt><dd>{polarityLabels[candidate.polarity]} · {epistemicLabels[candidate.epistemic_status]}<br/>{reportingLabels[candidate.reporting_mode]} · {temporalLabels[candidate.temporal_scope]}</dd></div>
    </dl>
    {candidate.endpoint_a_semantic_target === "NARRATOR_ROLE" || candidate.endpoint_b_semantic_target === "NARRATOR_ROLE" ? <p className="safety-note">Endpoint linguístico: narrador. Selecione uma Pessoa existente explicitamente; nenhuma identidade é presumida.</p> : null}
    {question && <p className="safety-note">Relação mencionada em uma pergunta — pode ser revisada, mas não registrada como declaração factual.</p>}
    {!item.eligible && <p className="blocker"><strong>BLOQUEADA</strong> — {blockerLabels[item.primary_blocker] ?? item.primary_blocker}</p>}
    <div className="relation-bindings">
      <label>Endpoint A — Pessoa LifeGraph<select value={personA} disabled={terminal || Boolean(busy)} onChange={(event) => { setPersonA(event.target.value); onPersonFocus([event.target.value, personB].filter(Boolean)); }}><option value="">Selecione explicitamente…</option>{people.map((person) => <option key={person.person_id} value={person.person_id}>{person.display_name}</option>)}</select></label>
      <label>Endpoint B — Pessoa LifeGraph<select value={personB} disabled={terminal || Boolean(busy)} onChange={(event) => { setPersonB(event.target.value); onPersonFocus([personA, event.target.value].filter(Boolean)); }}><option value="">Selecione explicitamente…</option>{people.map((person) => <option key={person.person_id} value={person.person_id}>{person.display_name}</option>)}</select></label>
    </div>
    <div className="actions"><button className="primary" disabled={terminal || Boolean(busy)} onClick={() => void accept()}>{busy === "accept" ? "Aceitando…" : "Aceitar relação"}</button><button className="secondary" disabled={terminal || Boolean(busy)} onClick={() => void reject()}>{busy === "reject" ? "Rejeitando…" : "Rejeitar relação"}</button>{item.review_status === "ACCEPTED_FOR_PERSISTENCE" && item.eligible && <button className="primary persist" disabled={Boolean(busy)} onClick={() => void persist()}>{busy === "persist" ? "Persistindo…" : item.persistence_status === "PERSISTED" ? "Ver declaração persistida" : "Persistir declaração"}</button>}</div>
    {message && <p className={item.eligible ? "success" : "error"} role="status">{message}</p>}
  </article>;
}

export function RelationReviewPanel({ people, review, onReviewChange, onGraphRefresh, onPersonFocus, embedded = false }: Props) {
  function update(item: RelationReviewItem) { onReviewChange({ ...review, candidates: review.candidates.map((candidate) => candidate.candidate_id === item.candidate_id ? item : candidate) }); }
  const content = <>
    <div className="relation-review-heading"><p className="stage-label">Relações familiares extraídas</p><h3 id="relation-review-title">Relações mencionadas na narrativa</h3></div>
    <p className="hint">Confira cada relação identificada e escolha explicitamente as duas pessoas correspondentes. Uma relação salva permanece uma declaração, não um fato confirmado.</p>
    {review.candidates.length === 0 ? <p className="empty">Nenhuma relação familiar explícita foi detectada.</p> : <div className="candidate-list">{review.candidates.map((item) => <RelationCard key={item.candidate_id} item={item} people={people} onUpdate={update} onGraphRefresh={onGraphRefresh} onPersonFocus={onPersonFocus}/>)}</div>}
  </>;
  return embedded ? <div className="relation-review-panel embedded-relation-review" aria-labelledby="relation-review-title">{content}</div> : <section className="panel stage-panel relation-review-panel" aria-labelledby="relation-review-title">{content}</section>;
}
