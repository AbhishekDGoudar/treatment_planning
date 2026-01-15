from datetime import datetime
from typing import Any, Dict, List, Optional

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


def list_documents(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    sort_by: str = "updated_at",
    sort_dir: str = "DESC",
) -> List[Dict[str, Any]]:
    skip = max(page - 1, 0) * page_size
    safe_sort_fields = {"updated_at", "uploaded_at", "state", "program_title", "waiver_number", "doc_id"}
    sort_field = sort_by if sort_by in safe_sort_fields else "updated_at"
    direction = "ASC" if sort_dir.upper() == "ASC" else "DESC"

    query = """
    MATCH (d:Document)
    WHERE $search IS NULL
       OR toLower(d.program_title) CONTAINS toLower($search)
       OR toLower(d.state) CONTAINS toLower($search)
       OR toLower(d.waiver_number) CONTAINS toLower($search)
       OR toLower(d.doc_id) CONTAINS toLower($search)
    RETURN d
    ORDER BY d.__SORT_FIELD__ __SORT_DIR__
    SKIP $skip
    LIMIT $limit
    """
    query = query.replace("__SORT_FIELD__", sort_field).replace("__SORT_DIR__", direction)

    with _driver().session(database=config.NEO4J_DATABASE) as session:
        rows = session.run(query, skip=skip, limit=page_size, search=search)
        results = []
        for row in rows:
            node = row["d"]
            results.append(dict(node))
        return results


def count_documents(search: Optional[str] = None) -> int:
    query = """
    MATCH (d:Document)
    WHERE $search IS NULL
       OR toLower(d.program_title) CONTAINS toLower($search)
       OR toLower(d.state) CONTAINS toLower($search)
       OR toLower(d.waiver_number) CONTAINS toLower($search)
       OR toLower(d.doc_id) CONTAINS toLower($search)
    RETURN count(d) AS total
    """
    with _driver().session(database=config.NEO4J_DATABASE) as session:
        row = session.run(query, search=search).single()
        return int(row["total"] or 0)
