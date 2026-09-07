export type CivilEventType = "nascimento" | "casamento" | "obito" | "natimorto";
export type SubjectResolution = "RESOLVED" | "UNRESOLVED";
export type ReviewStatus = "PENDING" | "ACCEPTED" | "REJECTED";

export interface Person {
  person_id: string;
  display_name: string;
  created_at: string;
  external_ref_person_id: string | null;
}

export interface NormalizedTimeCandidate {
  start: string;
  end: string;
  temporal_precision: "YEAR";
  normalization_method: "DETERMINISTIC_YEAR_PATTERN";
}

export interface ReviewCandidate {
  candidate_id: string;
  event_type: CivilEventType;
  trigger_text: string;
  trigger_start: number;
  trigger_end: number;
  subject_text: string | null;
  subject_resolution: SubjectResolution;
  subject_reason: string;
  participant_texts: string[];
  date_expression: string | null;
  normalized_time_candidate: NormalizedTimeCandidate | null;
  model_score_metadata: number | null;
  warnings: string[];
  review_status: ReviewStatus;
}

export interface ExtractionReview {
  extraction_id: string;
  source_text: string;
  model_id: string;
  model_revision: string;
  pipeline_id: "LIFEGRAPH_PT_CIVIL_V1";
  candidates: ReviewCandidate[];
  warnings: string[];
  latency_ms: number;
  expires_at: string;
}

export interface CandidateCorrections {
  event_type?: CivilEventType;
  subject_text?: string | null;
  participant_texts?: string[];
  date_expression?: string | null;
  claimed_date_start?: string;
  claimed_date_end?: string;
  temporal_precision?: "YEAR";
}

export interface CandidateAcceptanceRequest {
  person_id: string;
  corrections: CandidateCorrections;
}

export interface CandidateAcceptanceResult {
  extraction_id: string;
  candidate_id: string;
  person_id: string;
  claim_event_id: string;
  conversation_turn_id: string;
  origin: "CONVERSATION";
  verification_status: "DECLARED";
  correction_applied: boolean;
  created: boolean;
}

export interface GraphNode {
  id: string;
  type: "Person" | "ClaimEvent" | "RefEvent" | "ConversationTurn" | "Evidence";
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
