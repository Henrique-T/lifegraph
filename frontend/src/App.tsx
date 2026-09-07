import { useCallback, useEffect, useState } from "react";
import { acceptCandidate, extractNarrative, friendlyError, getGraph, listPersons, rejectCandidate } from "./api/client";
import type { CandidateAcceptanceRequest, ExtractionReview, GraphResponse, Person } from "./api/types";
import { CandidateCard } from "./components/CandidateCard";
import { GraphView } from "./components/GraphView";

export default function App() {
  const [text, setText] = useState("Eu me casei com Ana em 2019.");
  const [review, setReview] = useState<ExtractionReview | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    setLoading(true); setError(null); setReview(null);
    try { setReview(await extractNarrative(text.trim())); }
    catch (caught) { setError(friendlyError(caught)); }
    finally { setLoading(false); }
  }

  return <main>
    <header className="hero">
      <p className="eyebrow">INE5448 · UFSC · LifeGraph</p>
      <h1>LifeGraph Conversacional</h1>
      <p className="principle">Candidato da IA ≠ declaração aceita ≠ fato registral confirmado.</p>
    </header>

    <section className="panel" aria-labelledby="narrative-title">
      <h2 id="narrative-title">Narrativa</h2>
      <label htmlFor="narrative">Texto em português</label>
      <textarea id="narrative" rows={4} value={text} onChange={(event) => setText(event.target.value)} disabled={loading} />
      <button className="primary" type="button" onClick={extract} disabled={loading || !text.trim()}>{loading ? "Extraindo…" : "Extrair narrativa"}</button>
      <p className="hint">A extração cria apenas candidatos temporários e não altera o grafo.</p>
      {error && <p className="error" role="alert">{error}</p>}
    </section>

    <section className="panel" aria-labelledby="review-title">
      <div className="section-heading"><div><h2 id="review-title">Candidatos extraídos</h2>{review && <p>{review.candidates.length} candidato(s) · pipeline {review.pipeline_id}</p>}</div></div>
      {!review && <p className="empty">Execute uma extração para iniciar uma revisão.</p>}
      {review && <>
        <p className="expiry">Revisão temporária até {new Date(review.expires_at).toLocaleTimeString("pt-BR")}. Reiniciar o backend também a invalida.</p>
        {review.candidates.length === 0 && <p className="empty">Nenhum evento civil foi detectado.</p>}
        <div className="candidate-list">{review.candidates.map((candidate) =>
          <CandidateCard key={candidate.candidate_id} candidate={candidate} people={people} disabled={false}
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
        <details className="review-details"><summary>Detalhes da extração</summary><p>Modelo: {review.model_id}</p><p>Revisão: {review.model_revision}</p><p>ID: {review.extraction_id}</p></details>
      </>}
    </section>

    <section className="panel graph-panel" aria-labelledby="graph-title">
      <div className="section-heading"><div><h2 id="graph-title">LifeGraph</h2><p>{graph ? `${graph.nodes.length} nós · ${graph.edges.length} relações` : "Carregando grafo…"}</p></div><button className="secondary" type="button" onClick={() => void refreshGraph()}>Atualizar grafo</button></div>
      <GraphView graph={graph} />
      <div className="legend" aria-label="Significado dos estados">
        <p><strong>DECLARED</strong> Informação aceita da narrativa; ainda não confirmada por fonte registral.</p>
        <p><strong>CONFIRMED</strong> Declaração compatível com evidência REF após reconciliação.</p>
        <p><strong>DIVERGENT</strong> Declaração em conflito com evidência REF.</p>
        <p><strong>UNVERIFIED</strong> Evidência insuficiente. <strong>PROBABLE</strong> não é produzido atualmente.</p>
      </div>
    </section>
  </main>;
}
