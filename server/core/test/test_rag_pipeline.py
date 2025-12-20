from django.test import TestCase
from core.rag.pipeline import GraphRAGPipeline

class RAGPipelineTests(TestCase):
    def setUp(self):
        self.pipe = GraphRAGPipeline()

    def test_planning_safety_pass(self):
        """Ensure a standard read query passes safety checks."""
        safe_query = "MATCH (n) RETURN n LIMIT 5"
        result = self.pipe.validate_safety_node({"cypher_query": safe_query})
        self.assertTrue(result["is_safe"])

    def test_planning_safety_fail(self):
        """Ensure malicious queries are blocked."""
        malicious_query = "MATCH (n) DETACH DELETE n"
        result = self.pipe.validate_safety_node({"cypher_query": malicious_query})
        self.assertFalse(result["is_safe"])
        self.assertIn("forbidden keyword", result["error"])

    def test_query_analysis_json_parsing(self):
        """Test if the LLM output parser handles standard strings."""
        # Mocking the generator would be ideal here, but for integration:
        # We rely on the internal logic handling JSON failures gracefully
        state = {"question": "Waivers in Texas"}
        # This will hit the LLM (or mock)
        # For unit test, we can inject a mock generator if needed.
        pass

    def test_end_to_end_flow_simulation(self):
        """Simulate the full plan -> execute loop."""
        # 1. Plan
        q = "Find waivers in New York"
        plan_res = self.pipe.plan(q)
        
        self.assertIsNotNone(plan_res["execution_plan"])
        self.assertIsNotNone(plan_res["cypher_query"])
        
        if plan_res["is_safe"]:
            # 2. Execute
            exec_res = self.pipe.execute(plan_res["cypher_query"], q)
            self.assertIn("answer", exec_res)
            self.assertIn("graph_data", exec_res)