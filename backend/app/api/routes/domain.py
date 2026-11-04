"""CRUD, relationship, and graph-read routes for domain entities."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, status

from app.domain.schemas import (
    ClaimEventCreate,
    ClaimEventRead,
    ConversationTurnCreate,
    ConversationTurnRead,
    EvidenceCreate,
    EvidenceRead,
    GraphRead,
    ParticipationCreate,
    PersonCreate,
    PersonRead,
    RefEventCreate,
    RefEventRead,
    RelationshipRead,
)
from app.graph.repository import GraphRepository

router = APIRouter()


def get_repository(request: Request) -> GraphRepository:
    """Resolve the application-scoped graph repository."""
    return request.app.state.graph_repository


Repository = Annotated[GraphRepository, Depends(get_repository)]


@router.post("/persons", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
async def create_person(data: PersonCreate, repository: Repository) -> PersonRead:
    """Create a LifeGraph person."""
    return await repository.create_person(data)


@router.get("/persons", response_model=list[PersonRead])
async def list_persons(repository: Repository) -> list[PersonRead]:
    """List LifeGraph people."""
    return await repository.list_persons()


@router.get("/persons/{person_id}", response_model=PersonRead)
async def get_person(person_id: str, repository: Repository) -> PersonRead:
    """Read one LifeGraph person."""
    return await repository.get_person(person_id)


@router.post(
    "/conversation-turns",
    response_model=ConversationTurnRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_turn(
    data: ConversationTurnCreate, repository: Repository
) -> ConversationTurnRead:
    """Persist a conversation turn."""
    return await repository.create_conversation_turn(data)


@router.get(
    "/conversation-turns/{conversation_turn_id}",
    response_model=ConversationTurnRead,
)
async def get_conversation_turn(
    conversation_turn_id: str, repository: Repository
) -> ConversationTurnRead:
    """Read one conversation turn."""
    return await repository.get_conversation_turn(conversation_turn_id)


@router.post(
    "/claim-events",
    response_model=ClaimEventRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_claim_event(
    data: ClaimEventCreate, repository: Repository
) -> ClaimEventRead:
    """Create a conversational claim event."""
    return await repository.create_claim_event(data)


@router.get("/claim-events/{claim_event_id}", response_model=ClaimEventRead)
async def get_claim_event(
    claim_event_id: str, repository: Repository
) -> ClaimEventRead:
    """Read one claim event."""
    return await repository.get_claim_event(claim_event_id)


@router.post(
    "/ref-events", response_model=RefEventRead, status_code=status.HTTP_201_CREATED
)
async def create_ref_event(data: RefEventCreate, repository: Repository) -> RefEventRead:
    """Create a registral event."""
    return await repository.create_ref_event(data)


@router.get("/ref-events/{ref_event_id}", response_model=RefEventRead)
async def get_ref_event(ref_event_id: str, repository: Repository) -> RefEventRead:
    """Read one registral event."""
    return await repository.get_ref_event(ref_event_id)


@router.post(
    "/evidence", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED
)
async def create_evidence(data: EvidenceCreate, repository: Repository) -> EvidenceRead:
    """Create an evidence node."""
    return await repository.create_evidence(data)


@router.get("/evidence/{evidence_id}", response_model=EvidenceRead)
async def get_evidence(evidence_id: str, repository: Repository) -> EvidenceRead:
    """Read one evidence node."""
    return await repository.get_evidence(evidence_id)


@router.post(
    "/persons/{person_id}/claims/{claim_event_id}",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
async def link_person_claim(
    person_id: str, claim_event_id: str, repository: Repository
) -> RelationshipRead:
    """Bind a claim to its explicitly selected subject."""
    return await repository.link_person_claim(person_id, claim_event_id)


@router.post(
    "/claim-events/{claim_event_id}/source/{conversation_turn_id}",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
async def link_claim_source(
    claim_event_id: str, conversation_turn_id: str, repository: Repository
) -> RelationshipRead:
    """Link a claim to its source conversation turn."""
    return await repository.link_claim_source(claim_event_id, conversation_turn_id)


@router.post(
    "/persons/{person_id}/ref-events/{ref_event_id}/participation",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
async def link_person_ref_event(
    person_id: str,
    ref_event_id: str,
    data: ParticipationCreate,
    repository: Repository,
) -> RelationshipRead:
    """Link a person to a REF event with an explicit role."""
    return await repository.link_person_ref_event(person_id, ref_event_id, data.role)


@router.post(
    "/evidence/{evidence_id}/claims/{claim_event_id}",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
async def link_evidence_claim(
    evidence_id: str, claim_event_id: str, repository: Repository
) -> RelationshipRead:
    """Link evidence to the claim it explains."""
    return await repository.link_evidence_claim(evidence_id, claim_event_id)


@router.post(
    "/evidence/{evidence_id}/ref-events/{ref_event_id}",
    response_model=RelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
async def link_evidence_ref_event(
    evidence_id: str, ref_event_id: str, repository: Repository
) -> RelationshipRead:
    """Link evidence to a REF event it references."""
    return await repository.link_evidence_ref_event(evidence_id, ref_event_id)


@router.get("/graph", response_model=GraphRead)
async def get_graph(repository: Repository) -> GraphRead:
    """Return the normalized graph for visualization."""
    return await repository.get_graph()
