import { useEffect, useState } from "react";

type ServiceState = "checking" | "healthy" | "ready" | "unavailable";
type GraphSummary = { nodes: number; edges: number };

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8100";

export default function App() {
  const [api, setApi] = useState<ServiceState>("checking");
  const [neo4j, setNeo4j] = useState<ServiceState>("checking");
  const [graph, setGraph] = useState<GraphSummary | null>(null);

  useEffect(() => {
    async function checkServices() {
      try {
        const healthResponse = await fetch(`${apiBaseUrl}/health`);
        const health = await healthResponse.json();
        setApi(healthResponse.ok && health.status === "ok" ? "healthy" : "unavailable");
      } catch {
        setApi("unavailable");
      }

      try {
        const readyResponse = await fetch(`${apiBaseUrl}/ready`);
        const readiness = await readyResponse.json();
        setNeo4j(readyResponse.ok && readiness.neo4j === "ok" ? "ready" : "unavailable");
      } catch {
        setNeo4j("unavailable");
      }

      try {
        const graphResponse = await fetch(`${apiBaseUrl}/graph`);
        const graphData = await graphResponse.json();
        if (graphResponse.ok) {
          setGraph({ nodes: graphData.nodes.length, edges: graphData.edges.length });
        }
      } catch {
        setGraph(null);
      }
    }

    void checkServices();
  }, []);

  return (
    <main>
      <p className="eyebrow">INE5448 · UFSC · 2026.2</p>
      <h1>LifeGraph Conversacional</h1>
      <p className="principle">Narrative information is not registral fact.</p>
      <section aria-label="Infrastructure status">
        <p>API: <strong data-testid="api-status">{api}</strong></p>
        <p>Graph database: <strong data-testid="neo4j-status">{neo4j}</strong></p>
        <p>Graph nodes: <strong>{graph?.nodes ?? "unavailable"}</strong></p>
        <p>Graph edges: <strong>{graph?.edges ?? "unavailable"}</strong></p>
      </section>
      <p className="note">Infrastructure skeleton · no civil graph data created</p>
    </main>
  );
}
