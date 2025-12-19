from neo4j import GraphDatabase
from django.conf import settings

from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings


class GraphRetriever:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

        if settings.AI_PROVIDER.upper() == "OPENAI":
            self.embedder = OpenAIEmbeddings(
                model=settings.OPENAI_EMBEDDING_MODEL
            )
        else:
            self.embedder = OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDING_MODEL
            )

    def embed_query(self, query: str) -> list[float]:
        return self.embedder.embed_query(query)

    def retrieve_graph(self, query_vec: list[float], k: int = 5) -> dict:
        """
        Returns a real graph structure:
        nodes + edges
        """
        cypher = """
        CALL db.index.vector.queryNodes('waiver_embeddings', $k, $vector)
        YIELD node AS app, score

        MATCH (s:State)-[:HAS_APPLICATION]->(app)
        MATCH (app)-[:HAS_THEME]->(t:Theme)

        RETURN
            app.applicationNumber AS waiver_id,
            app.programTitle AS title,
            s.name AS state,
            collect(DISTINCT {
                type: "Theme",
                name: t.name,
                value: t.value
            }) AS themes,
            score
        ORDER BY score DESC
        """

        with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            records = [
                r.data() for r in session.run(
                    cypher,
                    vector=query_vec,
                    k=k
                )
            ]

        nodes = []
        edges = []

        for r in records:
            nodes.append({
                "id": r["waiver_id"],
                "type": "Waiver",
                "title": r["title"],
                "state": r["state"],
                "themes": r["themes"],
                "score": r["score"]
            })

            edges.append({
                "from": r["waiver_id"],
                "to": r["state"],
                "type": "LOCATED_IN"
            })

            for t in r["themes"]:
                edges.append({
                    "from": r["waiver_id"],
                    "to": t["name"],
                    "type": "HAS_THEME"
                })

        return {
            "nodes": nodes,
            "edges": edges
        }

    def close(self):
        self.driver.close()
