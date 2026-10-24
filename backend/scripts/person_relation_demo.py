"""Deterministic local fixture and real-API smoke flow for Person-Relation V1.

Run inside the configured backend container. This script is deliberately not an API
endpoint and only touches nodes carrying the fixed C4 demo Person identifiers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from neo4j import GraphDatabase


FIXTURE = {
    "joao": ("demo-person-rel-v1-joao", "João"),
    "maria": ("demo-person-rel-v1-maria", "Maria"),
    "pedro": ("demo-person-rel-v1-pedro", "Pedro"),
    "ana": ("demo-person-rel-v1-ana", "Ana"),
}
KINSHIP_EDGE_TYPES = {
    "FATHER_OF", "MOTHER_OF", "SON_OF", "DAUGHTER_OF",
    "BROTHER_OF", "SISTER_OF", "SPOUSE_OF",
}


def _driver():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )


def seed() -> dict[str, str]:
    """MERGE four synthetic Persons with stable identifiers and no claims."""

    with _driver() as driver, driver.session() as session:
        for person_id, name in FIXTURE.values():
            session.run(
                """
                MERGE (person:Person {person_id: $person_id})
                ON CREATE SET person.created_at = $created_at
                SET person.display_name = $name
                """,
                person_id=person_id,
                name=name,
                created_at=datetime.now(timezone.utc).isoformat(),
            ).consume()
    return {name: person_id for person_id, name in FIXTURE.values()}


def reset() -> dict[str, int]:
    """Remove only claims between marked demo Persons, then isolated demo Persons.

    ConversationTurns are removed only when they were linked to one of those claims
    and become unreferenced. Abandoned review turns are intentionally retained because
    they have no safe fixture marker in the frozen C1 schema.
    """

    ids = [item[0] for item in FIXTURE.values()]
    with _driver() as driver, driver.session() as session:
        row = session.run(
            """
            MATCH (claim:RelationClaim)-[:ENDPOINT_A|ENDPOINT_B]->(person:Person)
            WHERE person.person_id IN $ids
            WITH DISTINCT claim
            OPTIONAL MATCH (claim)-[:EXTRACTED_FROM]->(turn:ConversationTurn)
            DETACH DELETE claim
            WITH collect(DISTINCT turn) AS turns
            UNWIND turns AS turn
            WITH turn WHERE turn IS NOT NULL AND NOT ()-[:EXTRACTED_FROM]->(turn)
            DETACH DELETE turn
            RETURN count(turn) AS turns_removed
            """,
            ids=ids,
        ).single()
        persons_removed = session.run(
            """
            MATCH (person:Person)
            WHERE person.person_id IN $ids AND NOT (person)--()
            WITH collect(person) AS persons
            FOREACH (person IN persons | DELETE person)
            RETURN size(persons) AS removed
            """,
            ids=ids,
        ).single()["removed"]
    return {"persons_removed": persons_removed, "referenced_turns_removed": row["turns_removed"] if row else 0}


async def _post(client: httpx.AsyncClient, path: str, payload: dict[str, Any] | None = None) -> httpx.Response:
    return await client.post(path, json=payload or {})


async def smoke(api_base: str) -> dict[str, Any]:
    """Exercise positive, replay, independent, negated, and question flows."""

    people = seed()
    async with httpx.AsyncClient(base_url=api_base, timeout=30) as client:
        ready = await client.get("/ready")
        ready.raise_for_status()
        graph_before = (await client.get("/graph")).json()

        async def review(text: str) -> dict[str, Any]:
            response = await _post(client, "/relation-extractions", {"text": text})
            response.raise_for_status()
            return response.json()

        async def accept(review_data: dict[str, Any], endpoint_a: str, endpoint_b: str) -> httpx.Response:
            item = review_data["candidates"][0]
            return await _post(
                client,
                f'/relation-reviews/{review_data["review_id"]}/candidates/{item["candidate_id"]}/accept',
                {
                    "endpoint_a_person_id": endpoint_a,
                    "endpoint_b_person_id": endpoint_b,
                    "reviewer_accepted": True,
                    "corrections": {},
                },
            )

        positive = await review("João é pai de Maria.")
        accepted = await accept(positive, people["João"], people["Maria"])
        accepted.raise_for_status()
        item = positive["candidates"][0]
        path = f'/relation-reviews/{positive["review_id"]}/candidates/{item["candidate_id"]}/persist'
        first = await _post(client, path)
        first.raise_for_status()
        replay = await _post(client, path)
        replay.raise_for_status()

        independent = await review("João é pai de Maria.")
        independent_accept = await accept(independent, people["João"], people["Maria"])
        independent_accept.raise_for_status()
        independent_item = independent["candidates"][0]
        second = await _post(client, f'/relation-reviews/{independent["review_id"]}/candidates/{independent_item["candidate_id"]}/persist')
        second.raise_for_status()

        safety: dict[str, Any] = {}
        for key, text in (("negated", "João não é pai de Maria."), ("question", "João é pai de Maria?")):
            candidate_review = await review(text)
            blocked = await accept(candidate_review, people["João"], people["Maria"])
            blocked.raise_for_status()
            blocked_json = blocked.json()
            blocked_item = candidate_review["candidates"][0]
            persist_attempt = await _post(client, f'/relation-reviews/{candidate_review["review_id"]}/candidates/{blocked_item["candidate_id"]}/persist')
            safety[key] = {
                "candidate_count": len(candidate_review["candidates"]),
                "review_status": blocked_json["review_status"],
                "primary_blocker": blocked_json["primary_blocker"],
                "persist_http_status": persist_attempt.status_code,
            }

        narrator = await review("João é meu pai.")
        graph_after = (await client.get("/graph")).json()

    claim_ids = {first.json()["relation_claim_id"], second.json()["relation_claim_id"]}
    claim_nodes = [node for node in graph_after["nodes"] if node["type"] == "RelationClaim" and node["id"] in claim_ids]
    claim_edges = [edge for edge in graph_after["edges"] if edge["source"] in claim_ids]
    direct_fact_edges = [edge for edge in graph_after["edges"] if edge["type"] in KINSHIP_EDGE_TYPES]
    return {
        "ready": ready.json(),
        "graph_nodes_before": len(graph_before["nodes"]),
        "positive": {
            "candidate_type": positive["candidates"][0]["original_candidate"]["relation_type"],
            "endpoint_a": positive["candidates"][0]["original_candidate"]["endpoint_a_mention"],
            "endpoint_b": positive["candidates"][0]["original_candidate"]["endpoint_b_mention"],
            "accepted_status": accepted.json()["review_status"],
            "origin": first.json()["origin"],
            "verification_status": first.json()["verification_status"],
        },
        "replay": {"same_claim_id": first.json()["relation_claim_id"] == replay.json()["relation_claim_id"], "idempotent": replay.json()["idempotent_replay"]},
        "independent": {"claim_count": len(claim_nodes), "different_claim_ids": first.json()["relation_claim_id"] != second.json()["relation_claim_id"], "same_canonical_pair_key": first.json()["canonical_pair_key"] == second.json()["canonical_pair_key"]},
        "edges": {kind: sum(edge["type"] == kind for edge in claim_edges) for kind in ("ENDPOINT_A", "ENDPOINT_B", "EXTRACTED_FROM")},
        "direct_fact_edges": len(direct_fact_edges),
        "safety": safety,
        "narrator": {
            "endpoint_b_semantic_target": narrator["candidates"][0]["original_candidate"]["endpoint_b_semantic_target"],
            "endpoint_a_person": narrator["candidates"][0]["endpoint_a_person"],
            "endpoint_b_person": narrator["candidates"][0]["endpoint_b_person"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("seed", "reset", "smoke"))
    parser.add_argument("--api-base", default="http://backend:8100")
    args = parser.parse_args()
    if args.command == "seed":
        result = seed()
    elif args.command == "reset":
        result = reset()
    else:
        result = asyncio.run(smoke(args.api_base))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
