import type {
  CandidateAcceptanceRequest,
  CandidateAcceptanceResult,
  ExtractionReview,
  GraphResponse,
  Person,
  ReconciliationResult,
  RelationAcceptanceRequest,
  RelationActionResult,
  RelationPersistenceResult,
  RelationReviewSession,
} from "./types";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8100";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "Não foi possível conectar ao LifeGraph.");
  }
  const body = await response.json().catch(() => ({})) as { detail?: string };
  if (!response.ok) throw new ApiError(response.status, body.detail ?? "Falha na operação.");
  return body as T;
}

export const extractNarrative = (text: string) =>
  request<ExtractionReview>("/extractions", { method: "POST", body: JSON.stringify({ text }) });

export const getExtraction = (id: string) => request<ExtractionReview>(`/extractions/${id}`);
export const listPersons = () => request<Person[]>("/persons");
export const getGraph = () => request<GraphResponse>("/graph");
export const reconcileClaimEvent = (claimEventId: string) =>
  request<ReconciliationResult>(`/claim-events/${claimEventId}/reconcile`, { method: "POST" });
export const getClaimReconciliation = (claimEventId: string) =>
  request<ReconciliationResult>(`/claim-events/${claimEventId}/reconciliation`);

export const acceptCandidate = (extractionId: string, candidateId: string, data: CandidateAcceptanceRequest) =>
  request<CandidateAcceptanceResult>(`/extractions/${extractionId}/candidates/${candidateId}/accept`, {
    method: "POST", body: JSON.stringify(data),
  });

export const rejectCandidate = (extractionId: string, candidateId: string) =>
  request<{ review_status: "REJECTED" }>(`/extractions/${extractionId}/candidates/${candidateId}/reject`, {
    method: "POST",
  });

export const extractRelations = (text: string) => request<RelationReviewSession>("/relation-extractions", {
  method: "POST", body: JSON.stringify({ text }),
});
export const getRelationReview = (reviewId: string) => request<RelationReviewSession>(`/relation-reviews/${reviewId}`);
export const acceptRelationCandidate = (reviewId: string, candidateId: string, data: RelationAcceptanceRequest) =>
  request<RelationActionResult>(`/relation-reviews/${reviewId}/candidates/${candidateId}/accept`, { method: "POST", body: JSON.stringify(data) });
export const rejectRelationCandidate = (reviewId: string, candidateId: string, reason?: string) =>
  request<RelationActionResult>(`/relation-reviews/${reviewId}/candidates/${candidateId}/reject`, { method: "POST", body: JSON.stringify({ reason: reason || null }) });
export const persistRelationCandidate = (reviewId: string, candidateId: string) =>
  request<RelationPersistenceResult>(`/relation-reviews/${reviewId}/candidates/${candidateId}/persist`, { method: "POST", body: "{}" });

export function friendlyError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Ocorreu uma falha inesperada.";
  if (error.status === 404 && /person/i.test(error.message)) return "A Pessoa LifeGraph selecionada não foi encontrada.";
  if (error.status === 404 || error.status === 410) return "Esta revisão expirou. Execute a extração novamente.";
  if (error.status === 409) return "Este candidato já foi aceito com dados diferentes.";
  if (error.status === 422) return "Revise a pessoa e os campos corrigidos.";
  if (error.status === 503) return "O modelo de extração está indisponível no momento.";
  return error.message;
}

export function friendlyReconciliationError(error: unknown): string {
  if (!(error instanceof ApiError)) return "Não foi possível executar a reconciliação.";
  if (error.status === 404) return "A declaração não foi encontrada ou ainda não possui reconciliação.";
  if (error.status === 422) return "O identificador da declaração é inválido.";
  return "Não foi possível executar a comparação determinística com a evidência registral importada.";
}
