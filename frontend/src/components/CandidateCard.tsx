import { useState } from "react";
import type {
  CandidateAcceptanceRequest,
  CandidateAcceptanceResult,
  CivilEventType,
  Person,
  ReviewCandidate,
} from "../api/types";

const eventLabels: Record<CivilEventType, string> = {
  nascimento: "Nascimento", casamento: "Casamento", obito: "Óbito", natimorto: "Natimorto",
};

const reasonLabels: Record<string, string> = {
  EXPLICIT_FIRST_PERSON_PRONOUN: "Narrador indicado explicitamente",
  FIRST_PERSON_VERB_FORM: "Narrador indicado pela forma verbal em primeira pessoa",
  EXPLICIT_PRETRIGGER_SUBJECT: "Sujeito explícito próximo ao evento",
  EXPLICIT_SUBJECT_OVERRIDE: "Novo sujeito explícito identificado",
  RECONSTRUCTED_KINSHIP_SUBJECT: "Expressão de parentesco reconstruída no texto",
  COORDINATED_SUBJECT_CONTINUITY: "Sujeito mantido entre eventos coordenados",
  REPORTED_SPEECH_GUARD: "Atribuição evitada por contexto de fala reportada",
  INCIDENTAL_PERSON_GUARD: "Pessoa incidental não foi tratada como sujeito",
  POSSIBLE_COORDINATED_SUBJECT: "Possível sujeito composto; revisão necessária",
  CONFLICTING_SUBJECT_EVIDENCE: "Há indícios conflitantes sobre o sujeito",
  NO_SAFE_SUBJECT_EVIDENCE: "Não há evidência segura para resolver o sujeito",
  SENTENCE_BOUNDARY: "Continuidade interrompida entre sentenças",
};

function normalizeSearchText(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase("pt-BR");
}

interface Props {
  candidate: ReviewCandidate;
  people: Person[];
  disabled: boolean;
  onPersonSelectionChange: (personId: string) => void;
  onAccept: (request: CandidateAcceptanceRequest) => Promise<CandidateAcceptanceResult>;
  onReject: () => Promise<void>;
  onReviewComplete?: () => void;
}

export function CandidateCard({ candidate, people, disabled, onPersonSelectionChange, onAccept, onReject, onReviewComplete }: Props) {
  const originalYear = candidate.normalized_time_candidate?.temporal_precision === "YEAR"
    ? candidate.normalized_time_candidate.start.slice(0, 4) : "";
  const [personId, setPersonId] = useState("");
  const [personSearch, setPersonSearch] = useState("");
  const [personMenuOpen, setPersonMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [eventType, setEventType] = useState<CivilEventType>(candidate.event_type);
  const [participants, setParticipants] = useState(candidate.participant_texts.join(", "));
  const [year, setYear] = useState(originalYear);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [accepted, setAccepted] = useState<CandidateAcceptanceResult | null>(null);
  const [rejected, setRejected] = useState(candidate.review_status === "REJECTED");

  const changed = eventType !== candidate.event_type
    || participants !== candidate.participant_texts.join(", ") || year !== originalYear;

  async function accept() {
    if (!personId) { setError("Selecione explicitamente a Pessoa LifeGraph."); return; }
    if (year !== originalYear && !/^\d{4}$/.test(year)) {
      setError("Informe o ano corrigido com quatro dígitos.");
      return;
    }
    const corrections: CandidateAcceptanceRequest["corrections"] = {};
    if (eventType !== candidate.event_type) corrections.event_type = eventType;
    if (participants !== candidate.participant_texts.join(", ")) {
      corrections.participant_texts = participants.split(",").map((item) => item.trim()).filter(Boolean);
    }
    if (year !== originalYear) {
      corrections.date_expression = year;
      corrections.claimed_date_start = `${year}-01-01T00:00:00Z`;
      corrections.claimed_date_end = `${year}-12-31T23:59:59.999999Z`;
      corrections.temporal_precision = "YEAR";
    }
    setBusy(true); setError(null);
    try { setAccepted(await onAccept({ person_id: personId, corrections })); onReviewComplete?.(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Falha ao aceitar o evento extraído."); }
    finally { setBusy(false); }
  }

  async function reject() {
    setBusy(true); setError(null);
    try { await onReject(); setRejected(true); onReviewComplete?.(); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Falha ao rejeitar o evento extraído."); }
    finally { setBusy(false); }
  }

  const done = disabled || rejected || accepted !== null;
  const normalizedPersonSearch = normalizeSearchText(personSearch.trim());
  const visiblePeople = normalizedPersonSearch
    ? people.filter((person) => person.person_id === personId
      || normalizeSearchText(person.display_name).includes(normalizedPersonSearch))
    : people;

  return (
    <article className={`candidate ${candidate.subject_resolution.toLowerCase()}${accepted ? " accepted" : ""}`} aria-live="polite">
      <header className="candidate-header">
        <div><span className="kicker">Evento</span><h3>{eventLabels[candidate.event_type]}</h3></div>
        <span className={`status ${accepted ? "accepted" : rejected ? "rejected" : candidate.subject_resolution.toLowerCase()}`}>
          {accepted ? "ACEITO COMO DECLARAÇÃO" : rejected ? "REJEITADO" : candidate.subject_resolution === "RESOLVED" ? "SUJEITO A IDENTIFICAR" : "SUJEITO NÃO RESOLVIDO"}
        </span>
      </header>

      <dl className="candidate-facts">
        <div><dt>Trecho do evento</dt><dd>“{candidate.trigger_text}”</dd></div>
        <div><dt>Sujeito extraído</dt><dd>{candidate.subject_text === "__NARRATOR__" ? "Narrador" : candidate.subject_text ?? "Não resolvido"}</dd></div>
        <div><dt>Participantes</dt><dd>{candidate.participant_texts.join(", ") || "Nenhum identificado"}</dd></div>
        <div><dt>Data extraída</dt><dd>{candidate.date_expression ?? "Não identificada"}</dd></div>
      </dl>
      {candidate.subject_reason !== "FIRST_PERSON_VERB_FORM" && <p className="reason">{reasonLabels[candidate.subject_reason] ?? "Associação conservadora; revise antes de aceitar."}</p>}

      {candidate.subject_resolution === "UNRESOLVED" && !done && <p className="safety-note">Não foi possível determinar o sujeito com segurança. Selecione a pessoa correta ou rejeite o evento extraído.</p>}
      {!done && <div className="person-combobox">
        <label>Pessoa à qual esta declaração se refere
          <span className="combobox-input-wrap">
            <input
              type="search"
              value={personSearch}
              onFocus={() => setPersonMenuOpen(true)}
              onChange={(event) => {
                setPersonSearch(event.target.value);
                setPersonId("");
                setPersonMenuOpen(true);
                onPersonSelectionChange("");
              }}
              placeholder="Selecione ou digite um nome"
              autoComplete="off"
              role="combobox"
              aria-expanded={personMenuOpen}
              aria-controls={`person-options-${candidate.candidate_id}`}
            />
            <button type="button" className="combobox-toggle" aria-label="Mostrar lista de pessoas" aria-expanded={personMenuOpen} onClick={() => setPersonMenuOpen((open) => !open)}>⌄</button>
          </span>
        </label>
        {personMenuOpen && <div id={`person-options-${candidate.candidate_id}`} className="person-options" role="listbox" aria-label="Pessoas disponíveis">
          {visiblePeople.length > 0 ? visiblePeople.map((person) => <button key={person.person_id} type="button" role="option" aria-selected="false" onClick={() => {
            setPersonId(person.person_id);
            setPersonSearch(person.display_name);
            setPersonMenuOpen(false);
            onPersonSelectionChange(person.person_id);
          }}><strong>{person.display_name}</strong></button>) : <p>Nenhuma pessoa encontrada.</p>}
        </div>}
      </div>}

      {!done && <button className="link-button" type="button" onClick={() => setEditing(!editing)}>{editing ? "Fechar edição" : "Editar dados antes de aceitar"}</button>}
      {editing && !done && <fieldset className="corrections">
        <legend>Correções explícitas do revisor</legend>
        <label>Tipo do evento<select value={eventType} onChange={(e) => setEventType(e.target.value as CivilEventType)}>
          {Object.entries(eventLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
        <label>Participantes (separados por vírgula)<input value={participants} onChange={(e) => setParticipants(e.target.value)} /></label>
        <label>Ano normalizado<input inputMode="numeric" pattern="\d{4}" maxLength={4} value={year} onChange={(e) => setYear(e.target.value)} placeholder="AAAA" /></label>
        {changed && <div className="comparison"><strong>Original da IA</strong><span>{eventLabels[candidate.event_type]} · {candidate.subject_text ?? "não resolvido"} · {candidate.date_expression ?? "sem data"}</span><strong>Valor revisado</strong><span>{eventLabels[eventType]} · {candidate.subject_text ?? "não resolvido"} · {year || candidate.date_expression || "sem data"}</span></div>}
      </fieldset>}

      {error && <p className="error" role="alert">{error}</p>}
      {accepted && <p className="success" role="status">Declaração criada. Estado: DECLARADO.</p>}
      <div className="actions">
        <button type="button" className="primary" disabled={done || busy || !personId} onClick={accept}>Aceitar como declaração</button>
        <button type="button" className="secondary" disabled={done || busy} onClick={reject}>Rejeitar</button>
      </div>
    </article>
  );
}
