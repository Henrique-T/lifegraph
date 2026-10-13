import type { ReconciliationReasonCode } from "../api/types";

export type EvidenceTone = "match" | "divergence" | "uncertainty" | "neutral";

interface ReasonPresentation {
  title: string;
  description: string;
  tone: EvidenceTone;
}

export const reasonPresentation: Record<ReconciliationReasonCode, ReasonPresentation> = {
  NO_MATCHING_REF_EVENT_TYPE: {
    title: "Nenhum evento registral correspondente",
    description: "Nenhum evento registral do mesmo tipo foi encontrado para esta pessoa.",
    tone: "uncertainty",
  },
  INSUFFICIENT_TEMPORAL_EVIDENCE: {
    title: "Informação temporal insuficiente",
    description: "Não há informação temporal suficiente para comparação.",
    tone: "uncertainty",
  },
  EVENT_DATE_WITHIN_CLAIM_INTERVAL: {
    title: "Data compatível",
    description: "A data registral está dentro do intervalo declarado.",
    tone: "match",
  },
  EVENT_DATE_OUTSIDE_CLAIM_INTERVAL: {
    title: "Data incompatível",
    description: "A data registral está fora do intervalo declarado.",
    tone: "divergence",
  },
  UNIQUE_TEMPORALLY_COMPATIBLE_CANDIDATE: {
    title: "Evidência compatível identificada",
    description: "Existe um único evento registral temporalmente compatível.",
    tone: "match",
  },
  AMBIGUOUS_MULTIPLE_REF_CANDIDATES: {
    title: "Múltiplas evidências possíveis",
    description: "Há múltiplos eventos registrais compatíveis; não é possível escolher com segurança.",
    tone: "uncertainty",
  },
  NO_TEMPORALLY_COMPATIBLE_REF_EVENT: {
    title: "Nenhuma data registral compatível",
    description: "Nenhum evento registral é temporalmente compatível.",
    tone: "divergence",
  },
  EVENT_TYPE_MATCH: {
    title: "Tipo de evento correspondente",
    description: "O tipo da declaração coincide com o tipo do evento registral.",
    tone: "match",
  },
};

export function presentReason(value: unknown): ReasonPresentation {
  if (typeof value === "string" && value in reasonPresentation) {
    return reasonPresentation[value as ReconciliationReasonCode];
  }
  return {
    title: "Evidência de reconciliação",
    description: "Resultado determinístico registrado pelo mecanismo de reconciliação.",
    tone: "neutral",
  };
}

export const relationshipLabels: Record<string, string> = {
  SUBJECT_OF: "refere-se a",
  EXTRACTED_FROM: "extraída de",
  PARTICIPATES_IN: "participa de",
  ABOUT: "explica",
  DERIVED_FROM: "baseada em",
  SUPPORTED_BY: "apoiada por",
  CONTRADICTS: "diverge de",
};
