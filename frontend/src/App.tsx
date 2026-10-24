import { useCallback, useEffect, useState } from "react";
import { acceptCandidate, extractNarrative, friendlyError, getGraph, listPersons, reconcileClaimEvent, rejectCandidate } from "./api/client";
import type { CandidateAcceptanceRequest, ExtractionReview, GraphResponse, Person, ReconciliationResult } from "./api/types";
import { CandidateCard } from "./components/CandidateCard";
import { GraphView } from "./components/GraphView";
import { RelationReviewPanel } from "./components/RelationReviewPanel";

const canonicalDemoNarrative = "Nasci em 1988, casei em 2010 e me casei novamente em 2019.";

export default function App() {
  const [text, setText] = useState("");
  const [review, setReview] = useState<ExtractionReview | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewPersonSelections, setReviewPersonSelections] = useState<Record<string, string>>({});
  const [relationPersonSelections, setRelationPersonSelections] = useState<string[]>([]);

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
    setLoading(true); setError(null); setReview(null); setReviewPersonSelections({});
    try { setReview(await extractNarrative(text.trim())); }
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
    setError(null);
    setReviewPersonSelections({});
  }

  return <main>
    <header className="hero">
      <p className="eyebrow">INE5448 · UFSC · LifeGraph</p>
      <h1>LifeGraph Conversacional</h1>
      <p className="hero-summary">Narrativas pessoais, declarações revisadas e evidência registral em um grafo temporal com proveniência explícita.</p>
    </header>

    <section className="panel stage-panel" aria-labelledby="narrative-title">
      <div className="stage-heading"><span className="stage-number" aria-hidden="true">A</span><div><p className="stage-label">Narrativa e extração</p><h2 id="narrative-title">Conte sua trajetória</h2></div></div>
      <textarea id="narrative" aria-label="Narrativa pessoal" placeholder="Eu me casei com Ana em 2019." rows={4} value={text} onChange={(event) => setText(event.target.value)} disabled={loading} />
      <div className="narrative-actions">
        <button className="primary" type="button" onClick={extract} disabled={loading || !text.trim()}>{loading ? "Extraindo…" : "Extrair narrativa"}</button>
        <button className="secondary" type="button" onClick={loadCanonicalDemo} disabled={loading}>Carregar narrativa de demonstração</button>
      </div>
      <details className="demo-guide"><summary>Ver roteiro canônico em 5 passos</summary>
        <ol className="demo-steps"><li><span>1</span>Carregar narrativa</li><li><span>2</span>Extrair candidatos</li><li><span>3</span>Revisar e aceitar</li><li><span>4</span>Observar DECLARED</li><li><span>5</span>Reconciliar explicitamente</li></ol>
      </details>
      {error && <p className="error" role="alert">{error}</p>}
    </section>

    <section className="panel stage-panel" aria-labelledby="review-title">
      <div className="section-heading"><div className="stage-heading"><span className="stage-number" aria-hidden="true">B</span><div><p className="stage-label">Revisão e declaração</p><h2 id="review-title">Candidatos extraídos</h2>{review && <p>{review.candidates.length} {review.candidates.length === 1 ? "candidato encontrado" : "candidatos encontrados"}</p>}</div></div></div>
      {!review && <p className="empty">Execute uma extração para iniciar uma revisão.</p>}
      {review && <>
        <p className="expiry">Revisão temporária até {new Date(review.expires_at).toLocaleTimeString("pt-BR")}. Reiniciar o backend também a invalida.</p>
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
            }} />)}
        </div>
        <details className="review-details"><summary>Detalhes técnicos da extração</summary><p>Pipeline: {review.pipeline_id}</p><p>Modelo: {review.model_id}</p><p>Revisão: {review.model_revision}</p><p>ID: {review.extraction_id}</p></details>
      </>}
    </section>

    <RelationReviewPanel people={people} onGraphRefresh={refreshGraph} onPersonFocus={setRelationPersonSelections} />

    <section className="panel graph-panel stage-panel" aria-labelledby="graph-title">
      <div className="section-heading"><div className="stage-heading"><span className="stage-number" aria-hidden="true">C</span><div><p className="stage-label">Grafo e reconciliação</p><h2 id="graph-title">LifeGraph e proveniência</h2><p>{graph ? `${graph.nodes.length} nós · ${graph.edges.length} relações` : "Carregando grafo…"}</p></div></div><button className="secondary" type="button" onClick={() => void refreshGraph()}>Atualizar grafo</button></div>
      <GraphView graph={graph} focusedPersonIds={[...new Set([...Object.values(reviewPersonSelections).filter(Boolean), ...relationPersonSelections])]} onReconcile={reconcile} />
      <div className="legend" aria-label="Significado dos estados">
        <p><strong className="legend-status declared">DECLARED</strong><span>Declaração aceita; ainda não confirmada por evidência registral.</span></p>
        <p><strong className="legend-status confirmed">CONFIRMED</strong><span>Compatível com evidência registral.</span></p>
        <p><strong className="legend-status divergent">DIVERGENT</strong><span>Diverge da evidência registral disponível.</span></p>
        <p><strong className="legend-status unverified">UNVERIFIED</strong><span>Evidência insuficiente — não significa falso.</span></p>
      </div>
      <p className="probable-note"><strong>PROBABLE</strong> é um estado reservado e não é produzido atualmente.</p>
    </section>
  </main>;
}
