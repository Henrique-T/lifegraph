import cytoscape, { type ElementDefinition, type Position } from "cytoscape";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphNode, GraphResponse, ReconciliationResult } from "../api/types";
import { ReconciliationPanel } from "./ReconciliationPanel";
import { presentReason, relationshipLabels } from "./reconciliationPresentation";

const nodeColors: Record<string, string> = {
  Person: "#2563eb", ClaimEvent: "#7c3aed", RelationClaim: "#be185d", RefEvent: "#047857",
  ConversationTurn: "#b45309", Evidence: "#475569",
};

const eventColors: Record<string, string> = {
  nascimento: "#0284c7",
  casamento: "#c026d3",
  obito: "#64748b",
  natimorto: "#d97706",
};

type GraphViewMode = "focus" | "timeline";
type GraphViewVariant = "review" | "explorer";

const verificationStatusLabels: Record<string, string> = {
  DECLARED: "DECLARADO",
  CONFIRMED: "CONFIRMADO",
  DIVERGENT: "DIVERGE",
  UNVERIFIED: "NÃO VERIFICADO",
  PROBABLE: "PROVÁVEL",
};

function displayVerificationStatus(value: unknown): string {
  const status = String(value ?? "");
  return verificationStatusLabels[status] ?? status;
}

function normalizeSearchText(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
}

function focusedSubgraph(graph: GraphResponse, personIds: string[]): GraphResponse {
  const selectedPeople = new Set(personIds);
  const included = new Set(personIds);
  if (included.size === 0) return { nodes: [], edges: [] };

  const eventIds = new Set<string>();
  graph.edges.forEach((edge) => {
    if (selectedPeople.has(edge.source)) included.add(edge.target);
    if (selectedPeople.has(edge.target)) included.add(edge.source);
  });
  graph.nodes.forEach((node) => {
    if (included.has(node.id) && (node.type === "ClaimEvent" || node.type === "RelationClaim" || node.type === "RefEvent")) eventIds.add(node.id);
  });
  graph.edges.forEach((edge) => {
    if (eventIds.has(edge.source)) included.add(edge.target);
    if (eventIds.has(edge.target)) included.add(edge.source);
  });

  return {
    nodes: graph.nodes.filter((node) => included.has(node.id)),
    edges: graph.edges.filter((edge) => included.has(edge.source) && included.has(edge.target)),
  };
}

function timelineSubgraph(graph: GraphResponse, personId: string): GraphResponse {
  const focused = focusedSubgraph(graph, personId ? [personId] : []);
  const included = new Set(focused.nodes
    .filter((node) => node.type !== "RelationClaim" && (node.type !== "Person" || node.id === personId))
    .map((node) => node.id));
  return {
    nodes: focused.nodes.filter((node) => included.has(node.id)),
    edges: focused.edges.filter((edge) => included.has(edge.source) && included.has(edge.target)),
  };
}

function compactText(value: unknown, maximum = 28): string {
  const text = String(value ?? "").trim();
  return text.length > maximum ? `${text.slice(0, maximum - 1)}…` : text;
}

function nodeLabel(node: GraphNode): string {
  const p = node.properties;
  if (node.type === "Person") return `Pessoa\n${String(p.display_name ?? "")}`;
  if (node.type === "ClaimEvent") {
    const date = p.original_date_expression ?? (typeof p.claimed_date_start === "string" ? p.claimed_date_start.slice(0, 10) : null);
    return `Declaração\n${String(p.event_type ?? "")} · ${displayVerificationStatus(p.verification_status)}${date ? `\n${compactText(date)}` : ""}`;
  }
  if (node.type === "RelationClaim") return `RelationClaim\n${String(p.relation_type ?? "")} · ${displayVerificationStatus(p.verification_status ?? "DECLARED")}`;
  if (node.type === "RefEvent") {
    const date = typeof p.event_date === "string" ? p.event_date.slice(0, 10) : null;
    return `Evento REF\n${String(p.event_type ?? "")}${date ? `\n${date}` : ""}`;
  }
  if (node.type === "ConversationTurn") return `Narrativa\n${compactText(p.text)}`;
  return `Evidência\n${presentReason(p.evidence_type).title}`;
}

function normalizedEventDate(node: GraphNode): string | null {
  const value = node.type === "ClaimEvent"
    ? node.properties.claimed_date_start
    : node.type === "RefEvent" ? node.properties.event_date : null;
  return typeof value === "string" && !Number.isNaN(Date.parse(value)) ? value : null;
}

function dateColumnLabel(value: string | null): string {
  if (!value) return "Sem data normalizada";
  const datePart = value.slice(0, 10);
  return datePart.endsWith("-01-01") ? datePart.slice(0, 4) : datePart;
}

function timelineElements(graph: GraphResponse): {
  positions: Record<string, Position>;
  markers: ElementDefinition[];
} {
  const positions: Record<string, Position> = {};
  const eventNodes = graph.nodes.filter((node) => node.type === "ClaimEvent" || node.type === "RefEvent");
  const knownDates = [...new Set(eventNodes.map(normalizedEventDate).filter((value): value is string => Boolean(value)))]
    .sort((left, right) => Date.parse(left) - Date.parse(right));
  const hasUnknown = eventNodes.some((node) => normalizedEventDate(node) === null);
  const columns: Array<string | null> = [...knownDates, ...(hasUnknown ? [null] : [])];
  const markers: ElementDefinition[] = [];

  columns.forEach((date, columnIndex) => {
    const x = 180 + columnIndex * 230;
    const nodes = eventNodes.filter((node) => normalizedEventDate(node) === date);
    (["ClaimEvent", "RefEvent"] as const).forEach((type) => {
      const laneNodes = nodes.filter((node) => node.type === type);
      laneNodes.forEach((node, index) => {
        positions[node.id] = {
          x: x + (index - (laneNodes.length - 1) / 2) * 92,
          y: type === "ClaimEvent" ? 230 : 380,
        };
      });
    });
    markers.push({
      data: { id: `timeline-marker-${columnIndex}`, label: dateColumnLabel(date), type: "TimelineMarker" },
      position: { x, y: 135 },
      selectable: false,
      grabbable: false,
    });
  });

  const eventNodeById = new Map(eventNodes.map((node) => [node.id, node]));
  const relatedEventPosition = (nodeId: string): Position | null => {
    const edge = graph.edges.find((item) =>
      (item.source === nodeId && eventNodeById.has(item.target))
      || (item.target === nodeId && eventNodeById.has(item.source)));
    if (!edge) return null;
    const eventId = eventNodeById.has(edge.source) ? edge.source : edge.target;
    return positions[eventId] ?? null;
  };

  graph.nodes.filter((node) => node.type === "Person").forEach((node, index) => {
    const connected = graph.edges
      .filter((edge) => edge.type === "SUBJECT_OF" && (edge.source === node.id || edge.target === node.id))
      .map((edge) => positions[edge.source === node.id ? edge.target : edge.source])
      .filter((position): position is Position => Boolean(position));
    positions[node.id] = {
      x: connected.length ? connected.reduce((sum, position) => sum + position.x, 0) / connected.length : 140 + index * 150,
      y: 35,
    };
  });

  const satelliteCounts = new Map<string, number>();
  graph.nodes.filter((node) => node.type === "ConversationTurn" || node.type === "Evidence").forEach((node, index) => {
    const anchor = relatedEventPosition(node.id);
    const lane = node.type === "ConversationTurn" ? 525 : 660;
    const key = `${node.type}-${anchor?.x ?? "unlinked"}`;
    const siblingIndex = satelliteCounts.get(key) ?? 0;
    satelliteCounts.set(key, siblingIndex + 1);
    positions[node.id] = {
      x: (anchor?.x ?? 140 + index * 120) + siblingIndex * 82,
      y: lane,
    };
  });

  return { positions, markers };
}

function relatedNode(graph: GraphResponse, claimId: string, edgeType: string, nodeType: GraphNode["type"]): GraphNode | null {
  const edge = graph.edges.find((item) => item.type === edgeType && (item.source === claimId || item.target === claimId));
  if (!edge) return null;
  const relatedId = edge.source === claimId ? edge.target : edge.source;
  return graph.nodes.find((node) => node.id === relatedId && node.type === nodeType) ?? null;
}

function claimOptionLabel(claim: GraphNode, graph: GraphResponse): string {
  if (claim.type === "RelationClaim") {
    const endpointA = relatedNode(graph, claim.id, "ENDPOINT_A", "Person");
    const endpointB = relatedNode(graph, claim.id, "ENDPOINT_B", "Person");
    return `${String(claim.properties.relation_type ?? "relação")} · DECLARADO · ${String(endpointA?.properties.display_name ?? "?")} → ${String(endpointB?.properties.display_name ?? "?")}`;
  }
  const eventType = String(claim.properties.event_type ?? "evento");
  const status = displayVerificationStatus(claim.properties.verification_status ?? "sem estado");
  const date = String(claim.properties.original_date_expression ?? "sem data informada");
  const person = relatedNode(graph, claim.id, "SUBJECT_OF", "Person");
  const personName = String(person?.properties.display_name ?? "pessoa não identificada");
  return `${eventType} · ${status} · ${date} · ${personName}`;
}

function formatCreatedAt(value: unknown): string {
  if (typeof value !== "string") return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("pt-BR");
}

interface Props {
  graph: GraphResponse | null;
  focusedPersonIds: string[];
  onReconcile: (claimEventId: string) => Promise<ReconciliationResult>;
  variant?: GraphViewVariant;
}

export function GraphView({ graph, focusedPersonIds, onReconcile, variant = "review" }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<GraphViewMode>("focus");
  const [reviewPersonId, setReviewPersonId] = useState("");
  const [explorerPersonId, setExplorerPersonId] = useState("");
  const [explorerPersonSearch, setExplorerPersonSearch] = useState("");
  const [explorerPersonMenuOpen, setExplorerPersonMenuOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const availablePeople = useMemo(() => graph?.nodes.filter((node) => node.type === "Person") ?? [], [graph]);
  const normalizedExplorerSearch = normalizeSearchText(explorerPersonSearch.trim());
  const visibleExplorerPeople = normalizedExplorerSearch
    ? availablePeople.filter((person) => person.id === explorerPersonId
      || normalizeSearchText(String(person.properties.display_name ?? person.id)).includes(normalizedExplorerSearch))
    : availablePeople;
  useEffect(() => {
    if (!focusedPersonIds.includes(reviewPersonId)) setReviewPersonId(focusedPersonIds[0] ?? "");
  }, [focusedPersonIds, reviewPersonId]);
  useEffect(() => {
    if (!expanded) return;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setExpanded(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [expanded]);
  const reviewGraph = useMemo(() => graph ? focusedSubgraph(graph, reviewPersonId ? [reviewPersonId] : []) : null, [graph, reviewPersonId]);
  const reviewTimeline = useMemo(() => graph ? timelineSubgraph(graph, reviewPersonId) : null, [graph, reviewPersonId]);
  const explorerGraph = useMemo(() => graph ? focusedSubgraph(graph, explorerPersonId ? [explorerPersonId] : []) : null, [graph, explorerPersonId]);
  const explorerTimeline = useMemo(() => graph ? timelineSubgraph(graph, explorerPersonId) : null, [graph, explorerPersonId]);
  const visibleGraph = variant === "explorer"
    ? viewMode === "timeline" ? explorerTimeline : explorerGraph
    : viewMode === "timeline" ? reviewTimeline : reviewGraph;
  const selected = visibleGraph?.nodes.find((node) => node.id === selectedId) ?? null;
  const claims = visibleGraph?.nodes.filter((node) => node.type === "ClaimEvent" || node.type === "RelationClaim") ?? [];
  const selectedPerson = selected?.type === "ClaimEvent" && visibleGraph
    ? relatedNode(visibleGraph, selected.id, "SUBJECT_OF", "Person") : null;
  const selectedConversation = selected?.type === "ClaimEvent" && visibleGraph
    ? relatedNode(visibleGraph, selected.id, "EXTRACTED_FROM", "ConversationTurn") : null;
  const selectedRelationEndpointA = selected?.type === "RelationClaim" && visibleGraph ? relatedNode(visibleGraph, selected.id, "ENDPOINT_A", "Person") : null;
  const selectedRelationEndpointB = selected?.type === "RelationClaim" && visibleGraph ? relatedNode(visibleGraph, selected.id, "ENDPOINT_B", "Person") : null;
  const selectedRelationConversation = selected?.type === "RelationClaim" && visibleGraph ? relatedNode(visibleGraph, selected.id, "EXTRACTED_FROM", "ConversationTurn") : null;
  const selectedEvidence = selected?.type === "Evidence" ? presentReason(selected.properties.evidence_type) : null;
  useEffect(() => {
    if (!container.current || !visibleGraph) return;
    const timeline = timelineElements(visibleGraph);
    const cy = cytoscape({
      container: container.current,
      elements: [
        ...visibleGraph.nodes.map((node) => ({ data: { id: node.id, label: nodeLabel(node), type: node.type, eventType: String(node.properties.event_type ?? ""), status: String(node.properties.verification_status ?? ""), evidenceTone: node.type === "Evidence" ? presentReason(node.properties.evidence_type).tone : "" }, position: viewMode === "timeline" ? timeline.positions[node.id] : undefined })),
        ...visibleGraph.edges.map((edge, index) => ({ data: { id: `edge-${index}-${edge.source}-${edge.target}`, source: edge.source, target: edge.target, label: relationshipLabels[edge.type] ?? edge.type } })),
        ...(viewMode === "timeline" ? timeline.markers : []),
      ],
      layout: viewMode === "timeline"
        ? { name: "preset", animate: false, fit: true, padding: 32 }
        : { name: "cose", animate: false, padding: 24 },
      style: [
        { selector: "node", style: { "background-color": (element) => nodeColors[element.data("type")] ?? "#475569", label: "data(label)", color: "#f8fafc", "font-size": 11, "font-weight": 650, "text-wrap": "wrap", "text-valign": "center", width: 82, height: 82, "border-width": 2, "border-color": "#cbd5e1" } },
        { selector: 'node[type = "Person"]', style: { shape: "ellipse", width: 92, height: 92 } },
        { selector: 'node[type = "ClaimEvent"]', style: { shape: "round-rectangle", width: 112, height: 76 } },
        { selector: 'node[type = "RelationClaim"]', style: { shape: "round-diamond", width: 122, height: 92, "border-color": "#f9a8d4", "border-width": 5 } },
        { selector: 'node[type = "RefEvent"]', style: { shape: "diamond", width: 106, height: 106, "border-width": 3, "border-color": "#d1fae5" } },
        { selector: 'node[type = "ConversationTurn"]', style: { shape: "round-rectangle", width: 116, height: 66 } },
        { selector: 'node[type = "Evidence"]', style: { shape: "hexagon", width: 88, height: 76 } },
        ...Object.entries(eventColors).flatMap(([eventType, color]) => ([
          { selector: `node[type = "ClaimEvent"][eventType = "${eventType}"]`, style: { "background-color": color } },
          { selector: `node[type = "RefEvent"][eventType = "${eventType}"]`, style: { "background-color": color } },
        ])),
        { selector: 'node[type = "ClaimEvent"][status = "CONFIRMED"]', style: { "border-color": "#34d399", "border-width": 5 } },
        { selector: 'node[type = "ClaimEvent"][status = "DIVERGENT"]', style: { "border-color": "#fb7185", "border-width": 5 } },
        { selector: 'node[type = "ClaimEvent"][status = "UNVERIFIED"]', style: { "border-color": "#fbbf24", "border-width": 5 } },
        { selector: 'node[type = "ClaimEvent"][status = "DECLARED"]', style: { "border-color": "#60a5fa", "border-width": 5 } },
        { selector: 'node[type = "Evidence"][evidenceTone = "match"]', style: { "background-color": "#047857", "border-color": "#34d399" } },
        { selector: 'node[type = "Evidence"][evidenceTone = "divergence"]', style: { "background-color": "#881337", "border-color": "#fb7185" } },
        { selector: 'node[type = "Evidence"][evidenceTone = "uncertainty"]', style: { "background-color": "#78350f", "border-color": "#fbbf24" } },
        { selector: 'node[type = "TimelineMarker"]', style: { shape: "round-rectangle", width: 126, height: 30, "background-color": "#172554", "border-color": "#60a5fa", "border-width": 1, color: "#dbeafe", "font-size": 10, "font-weight": 750, "events": "no" } },
        { selector: "node:selected", style: { "border-color": "#ffffff", "border-width": 7, "overlay-color": "#93c5fd", "overlay-opacity": 0.15 } },
        { selector: "edge", style: { width: 2, "line-color": "#64748b", "target-arrow-color": "#64748b", "target-arrow-shape": "triangle", "curve-style": "bezier", label: "data(label)", "font-size": 9, color: "#e2e8f0", "text-background-color": "#0f172a", "text-background-opacity": 0.92, "text-background-padding": "2px" } },
      ],
    });
    cy.on("tap", 'node[type != "TimelineMarker"]', (event) => setSelectedId(event.target.id()));
    return () => cy.destroy();
  }, [visibleGraph, viewMode, expanded]);

  return <div className={expanded ? "graph-layout graph-expanded" : "graph-layout"}>
    <section className="graph-visual" aria-label="Visualização do LifeGraph">
      <button
        type="button"
        className="graph-expand-button"
        aria-label={expanded ? "Fechar visualização expandida" : "Expandir grafo para tela inteira"}
        title={expanded ? "Fechar visualização expandida" : "Expandir grafo"}
        aria-pressed={expanded}
        onClick={() => setExpanded((current) => !current)}
      >
        <span aria-hidden="true">{expanded ? "×" : "⛶"}</span>
      </button>
      {variant === "review" ? <>
      {focusedPersonIds.length > 0 && <label className="graph-person-selector">Pessoa da revisão<select value={reviewPersonId} onChange={(event) => setReviewPersonId(event.target.value)}>{focusedPersonIds.map((personId) => {
        const person = graph?.nodes.find((node) => node.type === "Person" && node.id === personId);
        return <option key={personId} value={personId}>{String(person?.properties.display_name ?? personId)}</option>;
      })}</select></label>}
      <div className="graph-toolbar" role="group" aria-label="Modo de visualização do grafo da revisão">
        <button type="button" className={viewMode === "focus" ? "view-mode active" : "view-mode"} aria-pressed={viewMode === "focus"} onClick={() => setViewMode("focus")}>Foco da revisão</button>
        <button type="button" className={viewMode === "timeline" ? "view-mode active" : "view-mode"} aria-pressed={viewMode === "timeline"} onClick={() => setViewMode("timeline")}>Linha do tempo</button>
      </div>
      {viewMode === "focus" && focusedPersonIds.length === 0 && <p className="timeline-note">Selecione uma pessoa em um evento extraído para visualizar somente seu subgrafo.</p>}
      {viewMode === "focus" && focusedPersonIds.length > 0 && <p className="timeline-note">Exibindo a pessoa escolhida e seus eventos, narrativas e evidências relacionados.</p>}
      {viewMode === "timeline" && <p className="timeline-note">Os eventos da pessoa escolhida são ordenados cronologicamente, da esquerda para a direita. Eventos sem data normalizada aparecem ao final.</p>}
      </> : <>
        <div className="person-combobox graph-person-selector">
          <label>Selecionar pessoa
            <span className="combobox-input-wrap">
              <input
                type="search"
                value={explorerPersonSearch}
                onFocus={() => setExplorerPersonMenuOpen(true)}
                onChange={(event) => {
                  setExplorerPersonSearch(event.target.value);
                  setExplorerPersonId("");
                  setExplorerPersonMenuOpen(true);
                }}
                placeholder="Selecione ou digite um nome"
                autoComplete="off"
                role="combobox"
                aria-expanded={explorerPersonMenuOpen}
                aria-controls="graph-person-options"
              />
              <button type="button" className="combobox-toggle" aria-label="Mostrar lista de pessoas" aria-expanded={explorerPersonMenuOpen} onClick={() => setExplorerPersonMenuOpen((open) => !open)}>⌄</button>
            </span>
          </label>
          {explorerPersonMenuOpen && <div id="graph-person-options" className="person-options" role="listbox" aria-label="Pessoas disponíveis">
            {visibleExplorerPeople.length > 0 ? visibleExplorerPeople.map((person) => <button key={person.id} type="button" role="option" aria-selected={person.id === explorerPersonId} onClick={() => {
              setExplorerPersonId(person.id);
              setExplorerPersonSearch(String(person.properties.display_name ?? person.id));
              setExplorerPersonMenuOpen(false);
            }}><strong>{String(person.properties.display_name ?? person.id)}</strong></button>) : <p>Nenhuma pessoa encontrada.</p>}
          </div>}
        </div>
        <div className="graph-toolbar" role="group" aria-label="Modo de visualização do grafo da pessoa selecionada">
          <button type="button" className={viewMode === "focus" ? "view-mode active" : "view-mode"} aria-pressed={viewMode === "focus"} onClick={() => setViewMode("focus")}>Grafo relacional</button>
          <button type="button" className={viewMode === "timeline" ? "view-mode active" : "view-mode"} aria-pressed={viewMode === "timeline"} onClick={() => setViewMode("timeline")}>Linha do tempo</button>
        </div>
        {!explorerPersonId && <p className="timeline-note">Escolha uma pessoa para visualizar seu grafo relacional completo.</p>}
        {explorerPersonId && viewMode === "focus" && <p className="timeline-note">Exibindo as declarações, relações e evidências vinculadas à pessoa selecionada.</p>}
        {explorerPersonId && viewMode === "timeline" && <p className="timeline-note">Os eventos civis são ordenados cronologicamente, da esquerda para a direita. Eventos sem data normalizada aparecem ao final.</p>}
      </>}
      <div ref={container} className="graph-canvas" role="img" aria-label={viewMode === "timeline" ? "Linha do tempo da pessoa selecionada" : variant === "explorer" ? "Grafo relacional da pessoa selecionada" : "Subgrafo da pessoa selecionada na revisão"} />
      <div className="graph-legends" aria-label="Legenda do grafo">
        <section><h4>Tipos de nó</h4><ul>
          <li><span className="node-key person" />Pessoa</li><li><span className="node-key claim" />Declaração de evento</li><li><span className="node-key relation-claim" />RelationClaim</li><li><span className="node-key ref" />Evento REF</li><li><span className="node-key conversation" />Narrativa</li><li><span className="node-key evidence" />Evidência</li>
        </ul></section>
        <section><h4>Tipos de evento</h4><ul>
          <li><span className="color-key birth" />Nascimento</li><li><span className="color-key marriage" />Casamento</li><li><span className="color-key death" />Óbito</li><li><span className="color-key stillbirth" />Natimorto</li>
        </ul></section>
        <section><h4>Estado da declaração</h4><ul>
          <li><span className="status-key declared" />Declarada</li><li><span className="status-key confirmed" />Confirmada</li><li><span className="status-key divergent" />Divergente</li><li><span className="status-key unverified" />Não verificada</li>
        </ul></section>
      </div>
    </section>
    <aside className={`provenance ${selected?.type === "ClaimEvent" ? "claim-selected" : ""}`} aria-live="polite">
      <p className="stage-label">Inspeção do nó selecionado</p><h3>Proveniência</h3>
      <label className="claim-selector">Inspecionar uma declaração salva
        <select value={selected?.type === "ClaimEvent" || selected?.type === "RelationClaim" ? selected.id : ""} onChange={(event) => setSelectedId(event.target.value || null)}>
          <option value="">Selecione no grafo ou escolha uma declaração…</option>
          {claims.map((claim) => <option key={claim.id} value={claim.id}>
            {visibleGraph ? claimOptionLabel(claim, visibleGraph) : claim.id}
          </option>)}
        </select>
        <small className="field-help">A lista contém os eventos declarados que já estão persistidos no LifeGraph. Selecione um para ver sua origem, seu estado e a reconciliação.</small>
      </label>
      {!selected && <p>Selecione um nó para inspecionar.</p>}
      {selected && <>
        <strong>{nodeLabel(selected).replaceAll("\n", " — ")}</strong>
        {selected.type === "ClaimEvent" && <dl>
          <div><dt>Pessoa</dt><dd>{String(selectedPerson?.properties.display_name ?? "—")}</dd></div>
          <div><dt>Origem</dt><dd>{String(selected.properties.origin ?? "—")}</dd></div>
          <div><dt>Status</dt><dd><span className={`inline-status ${String(selected.properties.verification_status ?? "").toLowerCase()}`}>{displayVerificationStatus(selected.properties.verification_status ?? "—")}</span></dd></div>
          <div className="provenance-wide"><dt>Narrativa original</dt><dd>“{String(selectedConversation?.properties.text ?? "—")}”</dd></div>
          <div><dt>Expressão temporal original</dt><dd>{String(selected.properties.original_date_expression ?? "Não informada")}</dd></div>
          <div><dt>Data normalizada</dt><dd>{selected.properties.claimed_date_start && selected.properties.claimed_date_end
            ? `${String(selected.properties.claimed_date_start)} até ${String(selected.properties.claimed_date_end)}`
            : "Não disponível"}</dd></div>
          <div><dt>Precisão temporal</dt><dd>{String(selected.properties.temporal_precision ?? "UNKNOWN")}</dd></div>
          <div><dt>Criada em</dt><dd>{formatCreatedAt(selected.properties.created_at)}</dd></div>
          <div><dt>Trecho do evento</dt><dd>{String(selected.properties.original_trigger_text ?? "—")}</dd></div>
          <div><dt>Correção</dt><dd>{selected.properties.reviewer_correction_applied ? "Sim" : "Não"}</dd></div>
          <div className="provenance-wide technical-identity"><dt>ID da declaração</dt><dd>{selected.id}</dd></div>
          <div className="provenance-wide technical-identity"><dt>Pipeline</dt><dd>{String(selected.properties.pipeline_id ?? "—")}</dd></div>
        </dl>}
        {selected.type === "RelationClaim" && <dl>
          <div><dt>Pessoa correspondente a “{String(selected.properties.accepted_endpoint_a_mention ?? selected.properties.original_endpoint_a_mention ?? "participante não resolvido")}”</dt><dd>{String(selectedRelationEndpointA?.properties.display_name ?? "—")}</dd></div>
          <div><dt>Pessoa correspondente a “{String(selected.properties.accepted_endpoint_b_mention ?? selected.properties.original_endpoint_b_mention ?? "participante não resolvido")}”</dt><dd>{String(selectedRelationEndpointB?.properties.display_name ?? "—")}</dd></div>
          <div><dt>Tipo declarado</dt><dd>{String(selected.properties.relation_type ?? "—")}</dd></div>
          <div><dt>Origem</dt><dd>{String(selected.properties.origin ?? "—")}</dd></div>
          <div><dt>Status</dt><dd><span className="inline-status declared">{displayVerificationStatus(selected.properties.verification_status ?? "DECLARED")}</span></dd></div>
          <div className="provenance-wide"><dt>Narrativa original</dt><dd>“{String(selectedRelationConversation?.properties.text ?? selected.properties.source_text ?? "—")}”</dd></div>
          <div><dt>Evidência aceita</dt><dd>{String(selected.properties.accepted_relation_surface ?? "—")}</dd></div>
          <div><dt>Evidência original</dt><dd>{String(selected.properties.original_relation_surface ?? "—")}</dd></div>
          <div><dt>Correção aplicada</dt><dd>{selected.properties.reviewer_correction_applied ? "Sim" : "Não"}</dd></div>
          <div><dt>Família estrutural</dt><dd>{String(selected.properties.canonical_relation_family ?? "—")}</dd></div>
          <div className="provenance-wide technical-identity"><dt>Claim ID</dt><dd><code>{selected.id}</code></dd></div>
          <div className="provenance-wide technical-identity"><dt>ConversationTurn</dt><dd><code>{selectedRelationConversation?.id ?? "—"}</code></dd></div>
          <div className="provenance-wide technical-identity"><dt>Revisão / extração</dt><dd><code>{String(selected.properties.review_id ?? "—")} / {String(selected.properties.candidate_id ?? "—")}</code></dd></div>
          <div className="provenance-wide technical-identity"><dt>Pipeline / configuração</dt><dd><code>{String(selected.properties.pipeline_id ?? "—")} / {String(selected.properties.configuration_hash ?? "—")}</code></dd></div>
          <div className="provenance-wide technical-identity"><dt>Canonical pair key</dt><dd><code>{String(selected.properties.canonical_pair_key ?? "—")}</code></dd></div>
        </dl>}
        {selected.type === "Evidence" && selectedEvidence && <>
          <div className={`evidence-summary evidence-${selectedEvidence.tone}`}>
            <span className="kicker">Resultado da comparação</span>
            <strong>{selectedEvidence.title}</strong>
            <p>{selectedEvidence.description}</p>
          </div>
          <dl>
            <div><dt>Origem</dt><dd>Mecanismo determinístico de reconciliação</dd></div>
            <div><dt>Criada em</dt><dd>{formatCreatedAt(selected.properties.created_at)}</dd></div>
          </dl>
          <details><summary>Detalhes técnicos</summary><dl>
            <div><dt>Código interno</dt><dd><code>{String(selected.properties.evidence_type ?? "—")}</code></dd></div>
            <div><dt>ID da evidência</dt><dd><code>{selected.id}</code></dd></div>
          </dl></details>
        </>}
        {selected.type === "ClaimEvent" && <ReconciliationPanel key={selected.id} claim={selected} graph={visibleGraph!} onReconcile={onReconcile} />}
      </>}
    </aside>
  </div>;
}
