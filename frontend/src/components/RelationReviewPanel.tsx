import { useState } from "react";
import { acceptRelationCandidate, extractRelations, friendlyError, persistRelationCandidate, rejectRelationCandidate } from "../api/client";
import type { Person, RelationCorrections, RelationReviewItem, RelationReviewSession, RelationType } from "../api/types";

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

interface Props { people: Person[]; onGraphRefresh: () => Promise<void>; onPersonFocus: (personIds: string[]) => void }

function SpanFields({ label, source, start, end, onChange }: { label: string; source: string; start: number; end: number; onChange: (start: number, end: number) => void }) {
  return <fieldset className="span-fields"><legend>{label}</legend>
    <label>Início <input type="number" min={0} max={source.length} value={start} onChange={(event) => onChange(Number(event.target.value), end)} /></label>
    <label>Fim <input type="number" min={0} max={source.length} value={end} onChange={(event) => onChange(start, Number(event.target.value))} /></label>
    <output>Trecho: “{source.slice(start, end)}”</output>
  </fieldset>;
}

function RelationCard({ item, people, onUpdate, onGraphRefresh, onPersonFocus }: { item: RelationReviewItem; people: Person[]; onUpdate: (item: RelationReviewItem) => void; onGraphRefresh: () => Promise<void>; onPersonFocus: (ids: string[]) => void }) {
  const candidate = item.corrected_candidate ?? item.original_candidate;
  const [personA, setPersonA] = useState(item.endpoint_a_person?.person_id ?? "");
  const [personB, setPersonB] = useState(item.endpoint_b_person?.person_id ?? "");
  const [relationType, setRelationType] = useState<RelationType>(candidate.relation_type);
  const [relationSpan, setRelationSpan] = useState([candidate.relation_span_start, candidate.relation_span_end]);
  const [endpointASpan, setEndpointASpan] = useState([candidate.endpoint_a_span_start ?? 0, candidate.endpoint_a_span_end ?? 0]);
  const [endpointBSpan, setEndpointBSpan] = useState([candidate.endpoint_b_span_start ?? 0, candidate.endpoint_b_span_end ?? 0]);
  const [swap, setSwap] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const question = item.source_text.trim().endsWith("?");
  const terminal = item.review_status === "REJECTED" || item.persistence_status === "PERSISTED";

  function corrections(): RelationCorrections {
    const result: RelationCorrections = { swap_endpoints: swap };
    if (relationType !== item.original_candidate.relation_type) result.relation_type = relationType;
    if (relationSpan[0] !== item.original_candidate.relation_span_start || relationSpan[1] !== item.original_candidate.relation_span_end)
      result.relation_surface = { start: relationSpan[0], end: relationSpan[1], text: item.source_text.slice(relationSpan[0], relationSpan[1]) };
    if (endpointASpan[0] !== (item.original_candidate.endpoint_a_span_start ?? 0) || endpointASpan[1] !== (item.original_candidate.endpoint_a_span_end ?? 0))
      result.endpoint_a = { start: endpointASpan[0], end: endpointASpan[1], text: item.source_text.slice(endpointASpan[0], endpointASpan[1]) };
    if (endpointBSpan[0] !== (item.original_candidate.endpoint_b_span_start ?? 0) || endpointBSpan[1] !== (item.original_candidate.endpoint_b_span_end ?? 0))
      result.endpoint_b = { start: endpointBSpan[0], end: endpointBSpan[1], text: item.source_text.slice(endpointBSpan[0], endpointBSpan[1]) };
    return result;
  }
  async function accept() {
    setBusy("accept"); setMessage(null);
    try {
      const result = await acceptRelationCandidate(item.review_id, item.candidate_id, { endpoint_a_person_id: personA || null, endpoint_b_person_id: personB || null, reviewer_accepted: true, corrections: corrections() });
      onUpdate(result.item); setMessage(result.eligible ? "Declaração aceita para persistência; ainda não é um fato confirmado." : blockerLabels[result.primary_blocker] ?? result.primary_blocker);
    } catch (error) { setMessage(friendlyError(error)); } finally { setBusy(null); }
  }
  async function reject() {
    setBusy("reject"); setMessage(null);
    try { onUpdate((await rejectRelationCandidate(item.review_id, item.candidate_id)).item); setMessage("Candidato rejeitado; nenhuma escrita no grafo foi realizada."); }
    catch (error) { setMessage(friendlyError(error)); } finally { setBusy(null); }
  }
  async function persist() {
    setBusy("persist"); setMessage(null);
    try {
      const result = await persistRelationCandidate(item.review_id, item.candidate_id);
      onUpdate({ ...item, persistence_status: "PERSISTED", relation_claim_id: result.relation_claim_id, persisted_at: result.persisted_at });
      setMessage(result.idempotent_replay ? `Declaração já persistida: ${result.relation_claim_id}` : `Declaração persistida como DECLARED: ${result.relation_claim_id}`);
      await onGraphRefresh();
    } catch (error) { setMessage(friendlyError(error)); } finally { setBusy(null); }
  }

  return <article className="candidate relation-candidate" aria-label={`Relação ${candidate.relation_type}`}>
    <header className="candidate-header"><div><span className="candidate-kind relation-kind">RELAÇÃO · interpretação automática</span><h3>{relationLabels[candidate.relation_type]} <code>{candidate.relation_type}</code></h3></div><span className={`status ${item.eligible ? "accepted" : "unresolved"}`}>{item.persistence_status === "PERSISTED" ? "PERSISTED · DECLARED" : item.review_status}</span></header>
    <blockquote className="source-narrative">{item.source_text}</blockquote>
    <dl className="candidate-facts">
      <div><dt>Evidência</dt><dd>“{candidate.relation_surface_text}”</dd></div><div><dt>Endpoint A</dt><dd>{candidate.endpoint_a_mention ?? "não resolvido"}<br/><small>{candidate.endpoint_a_semantic_target}</small></dd></div>
      <div><dt>Endpoint B</dt><dd>{candidate.endpoint_b_mention ?? "não resolvido"}<br/><small>{candidate.endpoint_b_semantic_target}</small></dd></div><div><dt>Dimensões</dt><dd>{candidate.polarity} · {candidate.epistemic_status}<br/>{candidate.reporting_mode} · {candidate.temporal_scope}</dd></div>
    </dl>
    {candidate.endpoint_a_semantic_target === "NARRATOR_ROLE" || candidate.endpoint_b_semantic_target === "NARRATOR_ROLE" ? <p className="safety-note">Endpoint linguístico: narrador. Selecione uma Pessoa existente explicitamente; nenhuma identidade é presumida.</p> : null}
    {question && <p className="safety-note">Relação mencionada em uma pergunta — pode ser revisada, mas não registrada como declaração factual.</p>}
    <p className={item.eligible ? "success" : "blocker"}><strong>{item.eligible ? "ELIGÍVEL" : "BLOQUEADA"}</strong> — {blockerLabels[item.primary_blocker] ?? item.primary_blocker}</p>
    <div className="relation-bindings">
      <label>Endpoint A — Pessoa LifeGraph<select value={personA} disabled={terminal || Boolean(busy)} onChange={(event) => { setPersonA(event.target.value); onPersonFocus([event.target.value, personB].filter(Boolean)); }}><option value="">Selecione explicitamente…</option>{people.map((person) => <option key={person.person_id} value={person.person_id}>{person.display_name}</option>)}</select></label>
      <label>Endpoint B — Pessoa LifeGraph<select value={personB} disabled={terminal || Boolean(busy)} onChange={(event) => { setPersonB(event.target.value); onPersonFocus([personA, event.target.value].filter(Boolean)); }}><option value="">Selecione explicitamente…</option>{people.map((person) => <option key={person.person_id} value={person.person_id}>{person.display_name}</option>)}</select></label>
    </div>
    <details><summary>Correções fundamentadas no texto</summary><div className="relation-corrections">
      <label>Tipo aceito<select value={relationType} onChange={(event) => setRelationType(event.target.value as RelationType)} disabled={terminal}>{Object.entries(relationLabels).map(([value, label]) => <option key={value} value={value}>{label} ({value})</option>)}</select></label>
      <SpanFields label="Evidência da relação" source={item.source_text} start={relationSpan[0]} end={relationSpan[1]} onChange={(start, end) => setRelationSpan([start, end])}/>
      <SpanFields label="Menção do endpoint A" source={item.source_text} start={endpointASpan[0]} end={endpointASpan[1]} onChange={(start, end) => setEndpointASpan([start, end])}/>
      <SpanFields label="Menção do endpoint B" source={item.source_text} start={endpointBSpan[0]} end={endpointBSpan[1]} onChange={(start, end) => setEndpointBSpan([start, end])}/>
      <label><input type="checkbox" checked={swap} onChange={(event) => setSwap(event.target.checked)} disabled={terminal}/> Trocar papéis A/B usando os mesmos trechos fundamentados</label>
      <small>Polaridade, estado epistêmico, modo de relato, tempo e proveniência são imutáveis.</small>
    </div></details>
    {item.corrected_candidate && <details><summary>Original e correção aceita</summary><p>Original: {item.original_candidate.relation_type} — “{item.original_candidate.relation_surface_text}”</p><p>Aceita: {item.corrected_candidate.relation_type} — “{item.corrected_candidate.relation_surface_text}”</p></details>}
    <div className="actions"><button className="primary" disabled={terminal || Boolean(busy)} onClick={() => void accept()}>{busy === "accept" ? "Aceitando…" : "Aceitar relação"}</button><button className="secondary" disabled={terminal || Boolean(busy)} onClick={() => void reject()}>{busy === "reject" ? "Rejeitando…" : "Rejeitar relação"}</button>{item.review_status === "ACCEPTED_FOR_PERSISTENCE" && item.eligible && <button className="primary persist" disabled={Boolean(busy)} onClick={() => void persist()}>{busy === "persist" ? "Persistindo…" : item.persistence_status === "PERSISTED" ? "Ver declaração persistida" : "Persistir declaração"}</button>}</div>
    {message && <p className={item.eligible ? "success" : "error"} role="status">{message}</p>}
    {item.relation_claim_id && <p className="success">RelationClaim <code>{item.relation_claim_id}</code> · origem CONVERSATION · status DECLARED</p>}
  </article>;
}

export function RelationReviewPanel({ people, onGraphRefresh, onPersonFocus }: Props) {
  const [text, setText] = useState(""); const [review, setReview] = useState<RelationReviewSession | null>(null);
  const [loading, setLoading] = useState(false); const [error, setError] = useState<string | null>(null);
  async function extract() { if (!text.trim()) return; setLoading(true); setError(null); setReview(null); try { setReview(await extractRelations(text.trim())); } catch (caught) { setError(friendlyError(caught)); } finally { setLoading(false); } }
  function update(item: RelationReviewItem) { setReview((current) => current ? { ...current, candidates: current.candidates.map((candidate) => candidate.candidate_id === item.candidate_id ? item : candidate) } : current); }
  return <section className="panel stage-panel relation-review-panel" aria-labelledby="relation-review-title">
    <div className="stage-heading"><span className="stage-number">R</span><div><p className="stage-label">Relações entre pessoas</p><h2 id="relation-review-title">Extrair e revisar declarações</h2></div></div>
    <p className="hint">Uma relação extraída é uma interpretação linguística. Mesmo persistida, permanece uma declaração <strong>DECLARED</strong>, não um fato confirmado.</p>
    <textarea aria-label="Narrativa para extração de relações" rows={3} value={text} onChange={(event) => setText(event.target.value)} placeholder="João é pai de Maria." disabled={loading}/>
    <button className="primary" disabled={loading || !text.trim()} onClick={() => void extract()}>{loading ? "Extraindo relações…" : "Extrair relações"}</button>
    {error && <p className="error" role="alert">{error}</p>}
    {review && <><p className="expiry">Revisão <code>{review.review_id}</code> válida até {new Date(review.expires_at).toLocaleTimeString("pt-BR")}. Reiniciar o backend também a invalida.</p>{review.candidates.length === 0 ? <p className="empty">Nenhuma relação explícita foi detectada.</p> : <div className="candidate-list">{review.candidates.map((item) => <RelationCard key={item.candidate_id} item={item} people={people} onUpdate={update} onGraphRefresh={onGraphRefresh} onPersonFocus={onPersonFocus}/>)}</div>}</>}
  </section>;
}
