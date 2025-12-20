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
        Original method kept for compatibility.
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
        return self.execute_raw_cypher(cypher, {"vector": query_vec, "k": k})

    def execute_raw_cypher(self, cypher: str, params: dict = None) -> dict:
        """
        Executes a generated Cypher query safely.
        """
        if params is None:
            params = {}
            
        with self.driver.session(database=settings.NEO4J_DATABASE) as session:
            try:
                records = [r.data() for r in session.run(cypher, **params)]
            except Exception as e:
                print(f"Cypher Execution Error: {e}")
                return {"nodes": [], "edges": []}

        nodes = []
        edges = []

        for r in records:
            # Dynamic parsing based on common return aliases
            # Use 'app' or 'waiver_id' if available
            wid = r.get("waiver_id") or r.get("app", {}).get("applicationNumber") or "unknown_id"
            title = r.get("title") or r.get("app", {}).get("programTitle") or "Untitled"
            state = r.get("state") or "Unknown State"
            themes = r.get("themes") or []
            score = r.get("score") or 0

            # Only add node if ID is valid
            if wid != "unknown_id":
                nodes.append({
                    "id": wid,
                    "type": "Waiver",
                    "title": title,
                    "state": state,
                    "themes": themes,
                    "score": score
                })

                edges.append({
                    "from": wid,
                    "to": state,
                    "type": "LOCATED_IN"
                })

                for t in themes:
                    if isinstance(t, dict) and "name" in t:
                        edges.append({
                            "from": wid,
                            "to": t["name"],
                            "type": "HAS_THEME"
                        })

        return {
            "nodes": nodes,
            "edges": edges
        }

    def close(self):
        self.driver.close()