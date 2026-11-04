import { useCallback, useEffect, useState } from "react";
import { acceptCandidate, extractNarrative, extractRelations, friendlyError, getGraph, listPersons, reconcileClaimEvent, rejectCandidate } from "./api/client";
import type { CandidateAcceptanceRequest, ExtractionReview, GraphResponse, Person, ReconciliationResult, RelationReviewSession } from "./api/types";
import { CandidateCard } from "./components/CandidateCard";
import { GraphView } from "./components/GraphView";
import { RelationReviewPanel } from "./components/RelationReviewPanel";

const canonicalDemoNarrative = "Nasci em 1988, casei em 2010 e me casei novamente em 2019.";
type WorkflowStage = "narrative" | "review" | "graph" | "complete";

function UpcomingStage({ marker, label, title }: { marker: string; label: string; title: string }) {
  return <section className="panel stage-panel collapsed-stage" aria-disabled="true">
    <div className="stage-heading"><span className="stage-number" aria-hidden="true">{marker}</span><div><p className="stage-label">{label}</p><h2>{title}</h2><p>Esta etapa será aberta quando a anterior for concluída.</p></div><span className="collapsed-chevron" aria-hidden="true">⌄</span></div>
  </section>;
}

function CompletedStage({ marker, label, title, onOpen }: { marker: string; label: string; title: string; onOpen: () => void }) {
  return <button className="panel stage-panel collapsed-stage completed-stage" type="button" onClick={onOpen} aria-label={`Reabrir etapa ${marker}: ${title}`}>
    <span className="stage-heading"><span className="stage-number completed-marker" aria-hidden="true">✓</span><span className="completed-stage-copy"><span className="stage-label">{label}</span><strong>{title}</strong><small>Etapa concluída — clique para revisar.</small></span><span className="collapsed-chevron" aria-hidden="true">⌃</span></span>
  </button>;
}

export default function App() {
  const [text, setText] = useState("");
  const [review, setReview] = useState<ExtractionReview | null>(null);
  const [relationReview, setRelationReview] = useState<RelationReviewSession | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewPersonSelections, setReviewPersonSelections] = useState<Record<string, string>>({});
  const [relationPersonSelections, setRelationPersonSelections] = useState<string[]>([]);
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage>("narrative");
  const [reviewedCandidateIds, setReviewedCandidateIds] = useState<string[]>([]);

  const refreshGraph = useCallback(async () => {
    try { setGraph(await getGraph()); }
    catch (caught) { setError(friendlyError(caught)); }
  }, []);

  useEffect(() => {
    void Promise.all([listPersons(), getGraph()])
      .then(([loadedPeople, loadedGraph]) => { setPeople(loadedPeople); setGraph(loadedGraph); })
      .catch((caught) => setError(friendlyError(caught)));
  }, []);

  async function extract() {
    if (!text.trim()) return;
    setLoading(true); setError(null); setReview(null); setRelationReview(null); setReviewPersonSelections({}); setRelationPersonSelections([]); setReviewedCandidateIds([]);
    try {
      const [eventResult, relationResult] = await Promise.all([extractNarrative(text.trim()), extractRelations(text.trim())]);
      setReview(eventResult); setRelationReview(relationResult); setWorkflowStage("review");
    }
    catch (caught) { setError(friendlyError(caught)); }
    finally { setLoading(false); }
  }

  async function reconcile(claimEventId: string): Promise<ReconciliationResult> {
    const result = await reconcileClaimEvent(claimEventId);
    await refreshGraph();
    return result;
  }

  function loadCanonicalDemo() {
    setText(canonicalDemoNarrative);
    setReview(null);
    setRelationReview(null);
    setError(null);
    setReviewPersonSelections({});
    setReviewedCandidateIds([]);
    setWorkflowStage("narrative");
  }

  function restartWithSameNarrative() {
    setReview(null);
    setRelationReview(null);
    setError(null);
    setReviewPersonSelections({});
    setRelationPersonSelections([]);
    setReviewedCandidateIds([]);
    setWorkflowStage("narrative");
  }

  const showAll = workflowStage === "complete";
  const eventReviewComplete = Boolean(review) && review!.candidates.every((candidate) => reviewedCandidateIds.includes(candidate.candidate_id));
  const relationReviewComplete = Boolean(relationReview) && relationReview!.candidates.every((candidate) => candidate.review_status === "REJECTED" || candidate.persistence_status === "PERSISTED");
  const reviewComplete = eventReviewComplete && relationReviewComplete;

  return <div className="app-shell">
    <aside className="dashboard-sidebar" aria-label="Navegação do LifeGraph">
      <div className="sidebar-brand">
        <span className="sidebar-mark" aria-hidden="true">LG</span>
        <div><strong>LifeGraph</strong><small>PoC conversacional</small></div>
      </div>
      <nav className="sidebar-nav" aria-label="Etapas da aplicação">
        <div className={workflowStage === "narrative" ? "current" : "completed"}><span>1</span>Narrativa</div>
        <div className={workflowStage === "review" ? "current" : workflowStage !== "narrative" ? "completed" : "pending"}><span>2</span>Revisão das extrações</div>
        <div className={["graph", "complete"].includes(workflowStage) ? "current" : "pending"}><span>3</span>Grafo e proveniência</div>
      </nav>
      <div className="sidebar-note">
        <strong>Revisão humana</strong>
        <p>Nenhuma interpretação é registrada como declaração sem revisão explícita.</p>
      </div>
      {workflowStage !== "narrative" && <button className="restart-flow" type="button" onClick={restartWithSameNarrative}>Começar do início com a mesma narrativa</button>}
      <p className="sidebar-footer">INE5448 · UFSC</p>
    </aside>
    <main className="dashboard-content">
    <header className="hero">
      <p className="eyebrow">INE5448 · UFSC · LifeGraph</p>
      <h1>LifeGraph Conversacional</h1>
      <p className="hero-summary">Narrativas pessoais, declarações revisadas e evidência registral em um grafo temporal com proveniência explícita.</p>
      <ol className="demo-steps workflow-overview" aria-label="Etapas realizadas pelo programa"><li><span>1</span>Lê a narrativa</li><li><span>2</span>Identifica eventos e relações</li><li><span>3</span>Aguarda sua revisão</li><li><span>4</span>Registra a declaração aceita</li><li><span>5</span>Compara eventos com o REF</li></ol>
    </header>

    {!showAll && workflowStage !== "narrative" && <div className="completed-stages">
      <CompletedStage marker="A" label="Narrativa e extração" title="Descreva a trajetória do cliente" onOpen={() => setWorkflowStage("narrative")}/>
      {workflowStage === "graph" && <CompletedStage marker="B" label="Revisão e declaração" title="Eventos e relações extraídos" onOpen={() => setWorkflowStage("review")}/>}
    </div>}

    <div className="workflow-stage" hidden={workflowStage !== "narrative" && !showAll}><section className="panel stage-panel" aria-labelledby="narrative-title">
      <div className="stage-heading"><span className="stage-number" aria-hidden="true">A</span><div><p className="stage-label">Narrativa e extração</p><h2 id="narrative-title">Descreva a trajetória do cliente</h2></div></div>
      <textarea id="narrative" aria-label="Narrativa pessoal" placeholder="Eu me casei com Ana em 2019." rows={4} value={text} onChange={(event) => setText(event.target.value)} disabled={loading} />
      <div className="narrative-actions">
        <button className="primary" type="button" onClick={extract} disabled={loading || !text.trim()}>{loading ? "Extraindo eventos e relações…" : "Extrair narrativa"}</button>
        <button className="secondary" type="button" onClick={loadCanonicalDemo} disabled={loading}>Carregar narrativa de demonstração</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </section>{workflowStage === "narrative" && <div className="upcoming-stages"><UpcomingStage marker="B" label="Revisão e declaração" title="Eventos e relações extraídos"/><UpcomingStage marker="C" label="Grafo e reconciliação" title="LifeGraph e proveniência"/></div>}</div>

    {review && relationReview && <div className="workflow-stage" hidden={workflowStage !== "review" && !showAll}><section className="panel stage-panel" aria-labelledby="review-title">
      <div className="section-heading"><div className="stage-heading"><span className="stage-number" aria-hidden="true">B</span><div><p className="stage-label">Revisão e declaração</p><h2 id="review-title">Eventos e relações extraídos</h2><p>{review.candidates.length} evento(s) · {relationReview.candidates.length} relação(ões)</p></div></div></div>
      <div className="review-subsection"><p className="stage-label">Eventos civis extraídos</p><h3>Eventos mencionados na narrativa</h3></div>
      {!review && <p className="empty">Execute uma extração para iniciar uma revisão.</p>}
      {review && <>
        {review.candidates.length === 0 && <p className="empty">Nenhum evento civil foi detectado.</p>}
        <div className="candidate-list">{review.candidates.map((candidate) =>
          <CandidateCard key={candidate.candidate_id} candidate={candidate} people={people} disabled={false}
            onPersonSelectionChange={(personId) => setReviewPersonSelections((current) => ({ ...current, [candidate.candidate_id]: personId }))}
            onAccept={async (request: CandidateAcceptanceRequest) => {
              try {
                const result = await acceptCandidate(review.extraction_id, candidate.candidate_id, request);
                await refreshGraph();
                return result;
              } catch (caught) { throw new Error(friendlyError(caught)); }
            }}
            onReject={async () => {
              try { await rejectCandidate(review.extraction_id, candidate.candidate_id); }
              catch (caught) { throw new Error(friendlyError(caught)); }
            }}
            onReviewComplete={() => setReviewedCandidateIds((current) => current.includes(candidate.candidate_id) ? current : [...current, candidate.candidate_id])} />)}
        </div>
      </>}
      <RelationReviewPanel people={people} review={relationReview} onReviewChange={setRelationReview} onGraphRefresh={refreshGraph} onPersonFocus={setRelationPersonSelections} embedded />
      {!showAll && <div className="stage-navigation"><button className="secondary" type="button" onClick={() => setWorkflowStage("narrative")}>Voltar para a narrativa</button><p>{reviewComplete ? "Todos os eventos e relações foram revisados." : "Aceite, persista ou rejeite cada item para continuar."}</p><button className="primary" type="button" disabled={!reviewComplete} onClick={() => setWorkflowStage("graph")}>Continuar para o grafo</button></div>}
    </section>{workflowStage === "review" && <div className="upcoming-stages"><UpcomingStage marker="C" label="Grafo e reconciliação" title="LifeGraph e proveniência"/></div>}</div>}

    {["graph", "complete"].includes(workflowStage) && <div className="workflow-stage" hidden={workflowStage !== "graph" && !showAll}><section className="panel graph-panel stage-panel" aria-labelledby="graph-title">
      <div className="section-heading"><div className="stage-heading"><span className="stage-number" aria-hidden="true">C</span><div><p className="stage-label">Grafo e reconciliação</p><h2 id="graph-title">LifeGraph e proveniência</h2><p>{graph ? `${graph.nodes.length} nós · ${graph.edges.length} relações` : "Carregando grafo…"}</p></div></div><button className="secondary" type="button" onClick={() => void refreshGraph()}>Atualizar grafo</button></div>
      <GraphView graph={graph} focusedPersonIds={[...new Set([...Object.values(reviewPersonSelections).filter(Boolean), ...relationPersonSelections])]} onReconcile={reconcile} variant="review" />
      <div className="legend" aria-label="Significado dos estados">
        <p><strong className="legend-status declared">DECLARADO</strong><span>Declaração aceita; ainda não confirmada por evidência registral.</span></p>
        <p><strong className="legend-status confirmed">CONFIRMADO</strong><span>Compatível com evidência registral.</span></p>
        <p><strong className="legend-status divergent">DIVERGE</strong><span>Diverge da evidência registral disponível.</span></p>
        <p><strong className="legend-status unverified">NÃO VERIFICADO</strong><span>Evidência insuficiente — não significa falso.</span></p>
      </div>
      <p className="probable-note"><strong>PROVÁVEL</strong> é um estado reservado e não é produzido atualmente.</p>
      {!showAll && <div className="stage-navigation"><button className="secondary" type="button" onClick={() => setWorkflowStage("review")}>Voltar para a revisão</button><button className="primary" type="button" onClick={() => setWorkflowStage("complete")}>Ver fluxo completo</button></div>}
    </section></div>}
    <section className="panel explorer-panel always-available-graph" aria-labelledby="explorer-title">
      <div className="stage-heading"><span className="stage-number" aria-hidden="true">G</span><div><p className="stage-label">Consulta independente</p><h2 id="explorer-title">Explorar grafo por pessoa</h2><p className="hint">Selecione qualquer pessoa existente no LifeGraph, independentemente da narrativa atual.</p></div></div>
      <GraphView graph={graph} focusedPersonIds={[]} onReconcile={reconcile} variant="explorer" />
    </section>
    </main>
  </div>;
}
