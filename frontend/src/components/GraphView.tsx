import cytoscape from "cytoscape";
import { useEffect, useRef, useState } from "react";
import type { GraphNode, GraphResponse, ReconciliationResult } from "../api/types";
import { ReconciliationPanel } from "./ReconciliationPanel";

const nodeColors: Record<string, string> = {
  Person: "#2563eb", ClaimEvent: "#7c3aed", RefEvent: "#047857",
  ConversationTurn: "#b45309", Evidence: "#475569",
};

function nodeLabel(node: GraphNode): string {
  const p = node.properties;
  if (node.type === "Person") return `Pessoa\n${String(p.display_name ?? "")}`;
  if (node.type === "ClaimEvent") return `Declaração\n${String(p.event_type ?? "")} · ${String(p.verification_status ?? "")}`;
  if (node.type === "RefEvent") return `Evento REF\n${String(p.event_type ?? "")}`;
  if (node.type === "ConversationTurn") return "Turno de conversa";
  return `Evidência\n${String(p.evidence_type ?? "")}`;
}

interface Props {
  graph: GraphResponse | null;
  onReconcile: (claimEventId: string) => Promise<ReconciliationResult>;
}

export function GraphView({ graph, onReconcile }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = graph?.nodes.find((node) => node.id === selectedId) ?? null;
  const claims = graph?.nodes.filter((node) => node.type === "ClaimEvent") ?? [];
  useEffect(() => {
    if (!container.current || !graph) return;
    const cy = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map((node) => ({ data: { id: node.id, label: nodeLabel(node), type: node.type } })),
        ...graph.edges.map((edge, index) => ({ data: { id: `edge-${index}-${edge.source}-${edge.target}`, source: edge.source, target: edge.target, label: edge.type } })),
      ],
      layout: { name: "cose", animate: false, padding: 24 },
      style: [
        { selector: "node", style: { "background-color": (element) => nodeColors[element.data("type")] ?? "#475569", label: "data(label)", color: "#f8fafc", "font-size": 10, "text-wrap": "wrap", "text-valign": "center", width: 74, height: 74 } },
        { selector: "edge", style: { width: 2, "line-color": "#64748b", "target-arrow-color": "#64748b", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(label)", "font-size": 8, color: "#cbd5e1", "text-background-color": "#0f172a", "text-background-opacity": 0.85 } },
      ],
    });
    cy.on("tap", "node", (event) => setSelectedId(event.target.id()));
    return () => cy.destroy();
  }, [graph]);

  return <div className="graph-layout">
    <div ref={container} className="graph-canvas" role="img" aria-label="Grafo LifeGraph com tipos identificados por texto e cor" />
    <aside className="provenance" aria-live="polite">
      <h3>Proveniência</h3>
      <label className="claim-selector">Declaração para inspeção
        <select value={selected?.type === "ClaimEvent" ? selected.id : ""} onChange={(event) => setSelectedId(event.target.value || null)}>
          <option value="">Selecione no grafo ou nesta lista…</option>
          {claims.map((claim) => <option key={claim.id} value={claim.id}>
            {String(claim.properties.event_type ?? "evento")} · {String(claim.properties.verification_status ?? "sem estado")} · {claim.id.slice(0, 8)}
          </option>)}
        </select>
      </label>
      {!selected && <p>Selecione um nó para inspecionar.</p>}
      {selected && <>
        <strong>{nodeLabel(selected).replace("\n", " — ")}</strong>
        {selected.type === "ClaimEvent" && <dl>
          <div><dt>Origem</dt><dd>{String(selected.properties.origin ?? "—")}</dd></div>
          <div><dt>Verificação</dt><dd>{String(selected.properties.verification_status ?? "—")}</dd></div>
          <div><dt>Trigger original</dt><dd>{String(selected.properties.original_trigger_text ?? "—")}</dd></div>
          <div><dt>Pipeline</dt><dd>{String(selected.properties.pipeline_id ?? "—")}</dd></div>
          <div><dt>Correção</dt><dd>{selected.properties.reviewer_correction_applied ? "Sim" : "Não"}</dd></div>
          <div><dt>Data declarada</dt><dd>{String(selected.properties.claimed_date_start ?? "—")} até {String(selected.properties.claimed_date_end ?? "—")}</dd></div>
        </dl>}
        {selected.type === "ClaimEvent" && <ReconciliationPanel key={selected.id} claim={selected} graph={graph!} onReconcile={onReconcile} />}
      </>}
    </aside>
  </div>;
}
