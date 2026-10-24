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

export type VerificationStatus = "DECLARED" | "PROBABLE" | "CONFIRMED" | "DIVERGENT" | "UNVERIFIED";

export type ReconciliationReasonCode =
  | "NO_MATCHING_REF_EVENT_TYPE"
  | "EVENT_TYPE_MATCH"
  | "EVENT_DATE_WITHIN_CLAIM_INTERVAL"
  | "EVENT_DATE_OUTSIDE_CLAIM_INTERVAL"
  | "INSUFFICIENT_TEMPORAL_EVIDENCE"
  | "UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE"
  | "NO_TEMPORALLY_COMPATIBLE_REF_EVENT"
  | "AMBIGUOUS_MULTIPLE_REF_CANDIDATES";

export interface ReconciliationResult {
  claim_event_id: string;
  status: VerificationStatus;
  matched_ref_event_id: string | null;
  candidate_ref_event_ids: string[];
  reason_codes: ReconciliationReasonCode[];
  reconciled_at: string;
}

export interface GraphNode {
  id: string;
  type: "Person" | "ClaimEvent" | "RelationClaim" | "RefEvent" | "ConversationTurn" | "Evidence";
  properties: Record<string, unknown>;
}

export type RelationType = "FATHER_OF" | "MOTHER_OF" | "SON_OF" | "DAUGHTER_OF" | "BROTHER_OF" | "SISTER_OF" | "SPOUSE_OF";
export type EndpointSemanticTarget = "EXPLICIT_MENTION" | "NARRATOR_ROLE" | "UNRESOLVED_MENTION";
export type RelationReviewStatus = "PENDING" | "BLOCKED" | "ACCEPTED_FOR_PERSISTENCE" | "REJECTED" | "EXPIRED";

export interface RelationCandidate {
  candidate_id: string; source_reference: string; source_text: string;
  relation_type: RelationType; relation_surface_text: string; relation_span_start: number; relation_span_end: number;
  endpoint_a_mention: string | null; endpoint_a_span_start: number | null; endpoint_a_span_end: number | null;
  endpoint_a_resolution_state: "RESOLVED_MENTION" | "UNRESOLVED_MENTION"; endpoint_a_semantic_target: EndpointSemanticTarget;
  endpoint_b_mention: string | null; endpoint_b_span_start: number | null; endpoint_b_span_end: number | null;
  endpoint_b_resolution_state: "RESOLVED_MENTION" | "UNRESOLVED_MENTION"; endpoint_b_semantic_target: EndpointSemanticTarget;
  polarity: "POSITIVE" | "NEGATED"; epistemic_status: "ASSERTED" | "UNCERTAIN" | "HYPOTHETICAL";
  reporting_mode: "DIRECT" | "REPORTED"; reporting_source_mention: string | null;
  temporal_scope: "CURRENT_OR_UNSPECIFIED" | "PAST" | "UNRESOLVED";
  warnings: string[]; pipeline_id: string; model_id: string; model_revision: string; configuration_hash: string;
  persistence_eligibility: string;
}

export interface GroundedSpan { text: string; start: number; end: number }
export interface RelationCorrections {
  relation_type?: RelationType; relation_surface?: GroundedSpan; endpoint_a?: GroundedSpan; endpoint_b?: GroundedSpan;
  endpoint_a_semantic_target?: EndpointSemanticTarget; endpoint_b_semantic_target?: EndpointSemanticTarget; swap_endpoints?: boolean;
}
export interface RelationReviewItem {
  review_id: string; candidate_id: string; source_text: string; original_candidate: RelationCandidate;
  corrected_candidate: RelationCandidate | null; corrections: RelationCorrections;
  endpoint_a_person: Person | null; endpoint_b_person: Person | null; review_status: RelationReviewStatus;
  eligible: boolean; primary_blocker: string; grounding_errors: string[]; rejection_reason: string | null;
  created_at: string; expires_at: string; persistence_status: "NOT_PERSISTED" | "PERSISTED";
  relation_claim_id: string | null; persisted_at: string | null;
}
export interface RelationReviewSession {
  review_id: string; source_text: string; conversation_turn_id: string; pipeline_id: "LIFEGRAPH_PERSON_RELATION_V1";
  model_id: string; model_revision: "A0_B2+B3+B4"; configuration_hash: string;
  candidates: RelationReviewItem[]; created_at: string; expires_at: string;
}
export interface RelationAcceptanceRequest {
  endpoint_a_person_id: string | null; endpoint_b_person_id: string | null; reviewer_accepted: true; corrections: RelationCorrections;
}
export interface RelationActionResult { review_id: string; candidate_id: string; review_status: RelationReviewStatus; eligible: boolean; primary_blocker: string; item: RelationReviewItem; idempotent_replay: boolean }
export interface RelationPersistenceResult {
  review_id: string; candidate_id: string; relation_claim_id: string; conversation_turn_id: string;
  review_status: "ACCEPTED_FOR_PERSISTENCE"; persistence_status: "PERSISTED"; relation_type: RelationType;
  endpoint_a_person_id: string; endpoint_b_person_id: string; canonical_pair_key: string;
  origin: "CONVERSATION"; verification_status: "DECLARED"; pipeline_id: string; model_revision: string;
  configuration_hash: string; persisted_at: string; idempotent_replay: boolean;
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
