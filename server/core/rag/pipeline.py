import json
from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, END
from .retriever import GraphRetriever
from .generator import GeneratorFactory, PromptPiece

# State Schema
class RAGState(TypedDict):
    question: str
    execution_plan: str
    cypher_query: str
    filters: Dict[str, Any]
    is_safe: bool
    graph_data: Dict[str, Any]
    answer: str
    error: str

class GraphRAGPipeline:
    def __init__(self):
        self.retriever = GraphRetriever()
        self.generator = GeneratorFactory()
        
        # Two distinct workflows
        self.planning_app = self._build_planning_workflow()
        self.execution_app = self._build_execution_workflow()

    def _build_planning_workflow(self):
        workflow = StateGraph(RAGState)
        workflow.add_node("analyze", self.analyze_query_node)
        workflow.add_node("draft_cypher", self.draft_cypher_node)
        workflow.add_node("validate", self.validate_safety_node)

        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "draft_cypher")
        workflow.add_edge("draft_cypher", "validate")
        workflow.add_edge("validate", END)
        return workflow.compile()

    def _build_execution_workflow(self):
        workflow = StateGraph(RAGState)
        workflow.add_node("execute_search", self.execute_search_node)
        workflow.add_node("generate_answer", self.generate_answer_node)

        workflow.set_entry_point("execute_search")
        workflow.add_edge("execute_search", "generate_answer")
        workflow.add_edge("generate_answer", END)
        return workflow.compile()

    # --- Planning Nodes ---
    def analyze_query_node(self, state: RAGState) -> RAGState:
        query = state["question"]
        prompt = [
            PromptPiece(role="system", content="Analyze the user question. Extract intent and filters. Output JSON with keys 'plan' (string) and 'filters' (dict)."),
            PromptPiece(role="user", content=f"Question: {query}")
        ]
        try:
            raw = self.generator.generate(prompt)
            data = json.loads(raw.replace("```json", "").replace("```", "").strip())
            return {"execution_plan": data.get("plan", "Run semantic search."), "filters": data.get("filters", {})}
        except:
            return {"execution_plan": "Run standard search.", "filters": {}}

    def draft_cypher_node(self, state: RAGState) -> RAGState:
        query = state["question"]
        filters = state.get("filters", {})
        
        prompt = [
            PromptPiece(
                role="system",
                content=(
                    "Write a READ-ONLY Cypher query for a Waiver Graph.\n"
                    "Schema: (State)-[:HAS_APPLICATION]->(WaiverApplication)-[:HAS_THEME]->(Theme)\n"
                    "WaiverApplication has index 'waiver_embeddings'.\n"
                    "IMPORTANT: If filtering by state, use 'WHERE toLower(s.name) CONTAINS ...'.\n"
                    "If concept search needed, use 'CALL db.index.vector.queryNodes(\"waiver_embeddings\", 10, $vector)'\n"
                    "RETURN waiver_id, title, state, themes, score."
                )
            ),
            PromptPiece(role="user", content=f"Question: {query}\nFilters: {filters}")
        ]
        
        cypher = self.generator.generate(prompt).strip().replace("```cypher", "").replace("```", "")
        return {"cypher_query": cypher}

    def validate_safety_node(self, state: RAGState) -> RAGState:
        cypher = state.get("cypher_query", "").upper()
        forbidden = ["CREATE", "DELETE", "MERGE", "DETACH", "SET", "DROP"]
        for term in forbidden:
            if term in cypher:
                return {"is_safe": False, "error": f"Forbidden keyword: {term}"}
        return {"is_safe": True}

    # --- Execution Nodes ---
    def execute_search_node(self, state: RAGState) -> RAGState:
        if not state.get("is_safe", False):
            return {"graph_data": {}}
        
        cypher = state["cypher_query"]
        params = {}
        
        # Inject embedding if required by generated cypher
        if "$vector" in cypher:
            params["vector"] = self.retriever.embed_query(state["question"])
            params["k"] = 10
            
        results = self.retriever.execute_raw_cypher(cypher, params)
        return {"graph_data": results}

    def generate_answer_node(self, state: RAGState) -> RAGState:
        graph = state["graph_data"]
        if not graph.get("nodes"):
            return {"answer": "I could not find relevant documents in the validated execution plan."}
            
        prompt = [
            PromptPiece(role="system", content="Answer using ONLY the provided graph data."),
            PromptPiece(role="user", content=f"Data: {json.dumps(graph)}\nQuestion: {state['question']}")
        ]
        return {"answer": self.generator.generate(prompt)}

    # --- API methods ---
    def plan(self, query: str) -> dict:
        return self.planning_app.invoke({
            "question": query, "filters": {}, "execution_plan": "", 
            "cypher_query": "", "is_safe": False, "graph_data": {}, "answer": "", "error": ""
        })

    def execute(self, cypher: str, question: str) -> dict:
        return self.execution_app.invoke({
            "question": question, "cypher_query": cypher, "is_safe": True,
            "filters": {}, "execution_plan": "", "graph_data": {}, "answer": "", "error": ""
        })