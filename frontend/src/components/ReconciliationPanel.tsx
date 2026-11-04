import { useState } from "react";
import { friendlyReconciliationError } from "../api/client";
import type { GraphNode, GraphResponse, ReconciliationReasonCode, ReconciliationResult, VerificationStatus } from "../api/types";
import { presentReason } from "./reconciliationPresentation";

const statusDescriptions: Record<VerificationStatus, string> = {
  DECLARED: "Declaração aceita da narrativa; ainda não reconciliada.",
  CONFIRMED: "Declaração compatível com evidência registral.",
  DIVERGENT: "Diverge da evidência registral disponível.",
  UNVERIFIED: "Evidência insuficiente — não significa que a declaração seja falsa.",
  PROBABLE: "Estado reservado; não produzido atualmente.",
};
const statusLabels: Record<VerificationStatus, string> = {
  DECLARED: "DECLARADO",
  CONFIRMED: "CONFIRMADO",
  DIVERGENT: "DIVERGE",
  UNVERIFIED: "NÃO VERIFICADO",
  PROBABLE: "PROVÁVEL",
};

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function refEvent(graph: GraphResponse, id: string | null): GraphNode | null {
  if (!id) return null;
  return graph.nodes.find((node) => node.type === "RefEvent" && node.id === id) ?? null;
}

function RefEventDetails({ node }: { node: GraphNode }) {
  return <dl className="ref-details">
    <div><dt>Tipo</dt><dd>{String(node.properties.event_type ?? "—")}</dd></div>
    <div><dt>Data do evento</dt><dd>{String(node.properties.event_date ?? "—")}</dd></div>
    <div><dt>Data do registro</dt><dd>{String(node.properties.registration_date ?? "—")}</dd></div>
    <div><dt>ID externo</dt><dd><code>{String(node.properties.external_ref_id ?? "—")}</code></dd></div>
  </dl>;
}

interface Props {
  claim: GraphNode;
  graph: GraphResponse;
  onReconcile: (claimEventId: string) => Promise<ReconciliationResult>;
}

export function ReconciliationPanel({ claim, graph, onReconcile }: Props) {
  const [result, setResult] = useState<ReconciliationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const graphStatus = String(claim.properties.verification_status ?? "DECLARED") as VerificationStatus;
  const status = result?.status ?? graphStatus;
  const reasonCodes = result?.reason_codes ?? stringArray(claim.properties.reconciliation_reason_codes) as ReconciliationReasonCode[];
  const candidateIds = result?.candidate_ref_event_ids ?? stringArray(claim.properties.reconciliation_candidate_ref_event_ids);
  const matchedId = result?.matched_ref_event_id ?? (typeof claim.properties.matched_ref_event_id === "string" ? claim.properties.matched_ref_event_id : null);
  const matched = refEvent(graph, matchedId);
  const candidates = candidateIds.map((id) => refEvent(graph, id)).filter((node): node is GraphNode => node !== null);
  const evidence = graph.edges
    .filter((edge) => edge.type === "ABOUT" && edge.target === claim.id)
    .map((edge) => graph.nodes.find((node) => node.id === edge.source && node.type === "Evidence"))
    .filter((node): node is GraphNode => node !== undefined);

  async function reconcile() {
    setBusy(true); setError(null);
    try { setResult(await onReconcile(claim.id)); }
    catch (caught) { setError(friendlyReconciliationError(caught)); }
    finally { setBusy(false); }
  }

  return <section className="reconciliation" aria-labelledby={`reconcile-${claim.id}`}>
    <h4 id={`reconcile-${claim.id}`}>Reconciliação determinística</h4>
    <div className={`reconciliation-status status-${status.toLowerCase()}`}>
      <strong>{statusLabels[status]}</strong><span>{statusDescriptions[status]}</span>
    </div>
    <p className="hint">Compara somente RefEvents já importados para a mesma Pessoa e o mesmo tipo de evento.</p>
    <button type="button" className="primary" disabled={busy} onClick={reconcile}>
      {busy ? "Reconciliando…" : "Reconciliar com evidência registral"}
    </button>
    {error && <p className="error" role="alert">{error}</p>}
    {reasonCodes.length > 0 && <div className="reason-list"><h5>Resultados determinísticos</h5><ul>
      {reasonCodes.map((code) => <li key={code} className={`reason-${presentReason(code).tone}`}>
        <strong>{presentReason(code).title}</strong><span>{presentReason(code).description}</span>
      </li>)}
    </ul><details><summary>Detalhes técnicos dos resultados</summary><ul>
      {reasonCodes.map((code) => <li key={code}><code>{code}</code></li>)}
    </ul></details></div>}
    {matched && <div className="registral-evidence"><h5>Evidência registral selecionada pelo motor</h5><RefEventDetails node={matched} /></div>}
    {candidates.length > 0 && <details><summary>Eventos registrais considerados ({candidates.length})</summary>
      {candidates.map((node) => <div key={node.id} className="candidate-ref"><RefEventDetails node={node} /></div>)}
    </details>}
    {evidence.length > 0 && <details><summary>Evidência determinística persistida ({evidence.length})</summary><ul>
      {evidence.map((node) => <li key={node.id}><strong>{presentReason(node.properties.evidence_type).title}</strong>: {presentReason(node.properties.evidence_type).description}</li>)}
    </ul></details>}
    {result && <small>Executada em {new Date(result.reconciled_at).toLocaleString("pt-BR")}.</small>}
  </section>;
}
