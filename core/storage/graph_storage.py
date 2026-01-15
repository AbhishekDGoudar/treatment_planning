from datetime import datetime
from typing import Any, Dict, List

from neo4j import GraphDatabase

from core import config


def _driver():
    return GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
    )


def upsert_document(doc_id: str, properties: Dict[str, Any]) -> None:
    props = dict(properties)
    props["doc_id"] = doc_id
    props["updated_at"] = datetime.utcnow().isoformat()

    state = props.get("state")

    query = """
    MERGE (d:Document {doc_id: $doc_id})
    SET d += $props
    WITH d
    FOREACH (_ IN CASE WHEN $state IS NULL OR $state = '' THEN [] ELSE [1] END |
        MERGE (s:State {code: $state})
        MERGE (d)-[:IN_STATE]->(s)
    )
    """

    with _driver().session(database=config.NEO4J_DATABASE) as session:
        session.run(query, doc_id=doc_id, props=props, state=state)


def list_documents(page: int = 1, page_size: int = 10) -> List[Dict[str, Any]]:
    skip = max(page - 1, 0) * page_size
    query = """
    MATCH (d:Document)
    RETURN d
    ORDER BY d.updated_at DESC
    SKIP $skip
    LIMIT $limit
    """

    with _driver().session(database=config.NEO4J_DATABASE) as session:
        rows = session.run(query, skip=skip, limit=page_size)
        results = []
        for row in rows:
            node = row["d"]
            results.append(dict(node))
        return results


def count_documents() -> int:
    query = "MATCH (d:Document) RETURN count(d) AS total"
    with _driver().session(database=config.NEO4J_DATABASE) as session:
        row = session.run(query).single()
        return int(row["total"] or 0)
