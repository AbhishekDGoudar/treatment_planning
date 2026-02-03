from typing import Optional, Callable

import pandas as pd
from neo4j import GraphDatabase

from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from core import config


def _get_provider_config(provider: str):
    if provider == "openai":
        return OpenAIEmbeddings(model=config.OPENAI_EMBEDDING_MODEL), 1536
    return OllamaEmbeddings(model=config.OLLAMA_EMBEDDING_MODEL, num_ctx=8192), 1024


def _safe_embed(embedder, text):
    if not text:
        return None
    safe_text = str(text)[:7000]
    try:
        return embedder.embed_query(safe_text)
    except Exception:
        return None


def ingest_statewise_kg(
    file_path: str,
    provider: str = "ollama",
    on_progress: Optional[Callable[[dict], None]] = None,
) -> dict:
    provider = provider.lower()
    embedder, dims = _get_provider_config(provider)

    df = pd.read_excel(file_path, dtype=str).fillna("")

    driver = GraphDatabase.driver(
        config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )

    created = 0
    with driver.session(database=config.NEO4J_DATABASE) as session:
        session.run("MATCH (n) DETACH DELETE n")
        session.run(
            f"""
            CREATE VECTOR INDEX waiver_embeddings IF NOT EXISTS
            FOR (w:WaiverApplication) ON (w.embedding)
            OPTIONS {{indexConfig: {{
              `vector.dimensions`: {dims},
              `vector.similarity_function`: 'cosine'
            }}}}
            """
        )

        for _, row in df.iterrows():
            app_num = str(row.get("Application Number", "")).strip()
            if not app_num:
                continue

            props = {
                "application_number": app_num,
                "program_title": str(row.get("What is the name of the waiver (1B)?", "")).strip(),
                "state": str(row.get("Which state (1A)?", "")).strip(),
                "year": str(row.get("Year", "")).strip(),
                "approved_date": str(row.get("Approved Effective Date (1E)", "")).strip(),
                "app_type": "AMENDMENT" if row.get("Amendment Number") else "NEW",
            }

            summary = f"{props['program_title']} in {props['state']}. {props['app_type']} application."
            props["embedding"] = _safe_embed(embedder, summary)

            themes = []
            for col, val in row.items():
                if col not in ["Application Number", "Which state (1A)?"] and str(val).strip():
                    themes.append(
                        {
                            "name": col,
                            "value": val,
                            "embedding": _safe_embed(embedder, f"{col}: {val}"),
                        }
                    )

            _cypher_ingest(session, props, themes)
            created += 1
            if on_progress:
                on_progress({"event": "row_ingested", "application_number": app_num})

    driver.close()
    return {"ingested": created}


def _cypher_ingest(session, props, themes):
    query = """
    MERGE (c:Country {name: 'United States'})
    MERGE (s:State {name: $props.state})
    MERGE (s)-[:LOCATED_IN]->(c)
    MERGE (c)-[:HAS_STATE]->(s)

    CREATE (w:WaiverApplication {
        applicationNumber: $props.application_number,
        programTitle: $props.program_title,
        year: $props.year,
        approvedDate: $props.approved_date,
        applicationType: $props.app_type,
        embedding: $props.embedding
    })

    MERGE (w)-[:SUBMITTED_BY]->(s)
    MERGE (s)-[:HAS_APPLICATION]->(w)

    WITH w
    UNWIND $themes AS tData
    CREATE (t:Theme {name: tData.name, value: tData.value, embedding: tData.embedding})

    CREATE (w)-[:HAS_THEME]->(t)
    CREATE (t)-[:BELONGS_TO]->(w)
    """
    session.run(query, props=props, themes=themes)
