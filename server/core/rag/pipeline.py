import json

from .retriever import GraphRetriever
from .generator import GeneratorFactory, PromptPiece


class GraphRAGPipeline:
    def __init__(self):
        self.retriever = GraphRetriever()
        self.generator = GeneratorFactory()

    def ask(self, query: str) -> dict:
        # 1️⃣ Embed once
        query_vec = self.retriever.embed_query(query)

        # 2️⃣ Retrieve evidence subgraph
        graph = self.retriever.retrieve_graph(query_vec)

        # 3️⃣ Build strict prompt
        prompt = [
            PromptPiece(
                role="system",
                content=(
            "You are a Graph-based Question Answering system.\n\n"
            "The provided data is a VERIFIED EVIDENCE GRAPH with the guaranteed structure:\n"
            "Country → State → Waiver Application → Themes.\n\n"
            "IMPORTANT CONSTRAINTS:\n"
            "1. Use ONLY facts explicitly present in the graph.\n"
            "2. Do NOT assume or infer missing information.\n"
            "3. Each waiver belongs to exactly one state and country.\n"
            "4. If requested information is missing, say so clearly.\n\n"
            "REASONING:\n"
            "- Identify relevant waiver nodes.\n"
            "- Use only directly connected nodes.\n"
            "- Do not merge facts unless explicitly asked.\n\n"
            "ANSWER FORMAT:\n"
            "- Concise, factual English.\n"
            "- Exact entity names from the graph.\n"
            "- Explicitly state if the graph lacks the answer.\n"
            )
        ),
        PromptPiece(
            role="user",
            content=f"""
                Graph Data (JSON):
                {json.dumps(graph, indent=2)}

                Question:
                {query}
                """
                    )
                ]

        # 4️⃣ Generate grounded answer
        answer = self.generator.generate(prompt)

        return {
            "answer": answer,
            "graph": graph
        }
