import os
import pandas as pd
from neo4j import GraphDatabase
from django.core.management.base import BaseCommand
from django.conf import settings

# Provider Imports
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

# Configuration
CENTRAL_NODE_NAME = "United States"

class Command(BaseCommand):
    help = (
        "Ingests Waiver data into Neo4j with a Hybrid GraphRAG approach. "
        "Creates traditional Nodes/Edges with Vector Embeddings for similarity search. "
        "Supports --provider [ollama|openai]."
    )

    def add_arguments(self, parser):
        parser.add_argument('--provider', type=str, default='ollama', help='ollama or openai')

    def get_provider_config(self, provider):
        """Returns the embedder and the required Neo4j index dimensions."""
        if provider == 'openai':
            # OpenAI text-embedding-3-small uses 1536 dims
            return OpenAIEmbeddings(model="text-embedding-3-small"), 1536
        else:
            # FIX: Explicitly set num_ctx to 8192 to prevent 400 Context Length errors
            # nomic-embed-text supports 8192, but Ollama defaults to 2048
            return OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDING_MODEL,
                num_ctx=8192  # BGE-M3 max sequence length
                ), 1024

    def safe_embed(self, embedder, text):
        """Truncates text to ensure it never exceeds model limits."""
        if not text: return None
        # Safety truncation: roughly 7k characters (~1800-2000 tokens)
        # This prevents the 'input length exceeds context' crash
        safe_text = str(text)[:7000]
        try:
            return embedder.embed_query(safe_text)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Skipping embedding for text: {e}"))
            return None

    def handle(self, *args, **options):
        provider = options['provider'].lower()
        embedder, dims = self.get_provider_config(provider)

        # 1. Load Data
        file_path = os.path.join(getattr(settings, 'DATA_ROOT', '.'), "SED Waiver Data - Treatment Planning.xlsx")
        df = pd.read_excel(file_path, dtype=str).fillna('')

        # 2. Neo4j Setup
        driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD))
        
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            self.stdout.write("Wiping DB and setting up Vector Index...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # Create Vector Index (STRICTLY matches the chosen provider's dimensions)
            session.run(f"""
                CREATE VECTOR INDEX waiver_embeddings IF NOT EXISTS
                FOR (w:WaiverApplication) ON (w.embedding)
                OPTIONS {{indexConfig: {{
                  `vector.dimensions`: {dims},
                  `vector.similarity_function`: 'cosine'
                }}}}
            """)

            # 3. Process Ingestion
            for _, row in df.iterrows():
                app_num = str(row.get("Application Number", "")).strip()
                if not app_num: continue

                # Prepare standard Waiver properties
                props = {
                    "application_number": app_num,
                    "program_title": str(row.get("What is the name of the waiver (1B)?", "")).strip(),
                    "state": str(row.get("Which state (1A)?", "")).strip(),
                    "year": str(row.get("Year", "")).strip(),
                    "approved_date": str(row.get("Approved Effective Date (1E)", "")).strip(),
                    "app_type": "AMENDMENT" if row.get("Amendment Number") else "NEW",
                }

                # Semantic Summary for Hybrid Search
                summary = f"{props['program_title']} in {props['state']}. {props['app_type']} application."
                props['embedding'] = self.safe_embed(embedder, summary)

                # Process all other columns as Theme nodes
                themes = []
                for col, val in row.items():
                    if col not in ["Application Number", "Which state (1A)?"] and str(val).strip():
                        themes.append({
                            "name": col, "value": val,
                            "embedding": self.safe_embed(embedder, f"{col}: {val}")
                        })

                self._cypher_ingest(session, props, themes)

        driver.close()
        self.stdout.write(self.style.SUCCESS(f"✅ Ingestion complete using {provider}"))

    def _cypher_ingest(self, session, props, themes):
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
        
        // Relationships (Traditional Format)
        MERGE (w)-[:SUBMITTED_BY]->(s)
        MERGE (s)-[:HAS_APPLICATION]->(w)

        WITH w
        UNWIND $themes AS tData
        CREATE (t:Theme {name: tData.name, value: tData.value, embedding: tData.embedding})
        
        // Bidirectional Theme Links
        CREATE (w)-[:HAS_THEME]->(t)
        CREATE (t)-[:BELONGS_TO]->(w)
        """
        session.run(query, props=props, themes=themes)