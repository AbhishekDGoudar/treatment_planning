from neo4j import GraphDatabase
from django.conf import settings

SCHEMA = '''
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.path IS UNIQUE;
CREATE CONSTRAINT year_val IF NOT EXISTS FOR (y:Year) REQUIRE y.value IS UNIQUE;
CREATE CONSTRAINT state_val IF NOT EXISTS FOR (s:State) REQUIRE s.code IS UNIQUE;
CREATE CONSTRAINT group_val IF NOT EXISTS FOR (g:Group) REQUIRE g.name IS UNIQUE;
'''

class Graph:
    def __init__(self):
        self.driver = GraphDatabase.driver(settings.NEO4J_URI, auth=(settings.NEO4J_USER, settings.NEO4J_PASS))
        with self.driver.session() as s:
            for stmt in SCHEMA.split(";"):
                if stmt.strip():
                    s.run(stmt)

    def upsert_doc(self, path: str, year: int | None, group: str | None, state: str | None):
        cypher = '''
        MERGE (d:Document {path:$path})
        WITH d
        FOREACH (_ IN CASE WHEN $year IS NULL THEN [] ELSE [1] END |
            MERGE (y:Year {value:$year}) MERGE (d)-[:HAS_YEAR]->(y))
        FOREACH (_ IN CASE WHEN $group IS NULL THEN [] ELSE [1] END |
            MERGE (g:Group {name:$group}) MERGE (d)-[:BELONGS_TO]->(g))
        FOREACH (_ IN CASE WHEN $state IS NULL THEN [] ELSE [1] END |
            MERGE (s:State {code:$state}) MERGE (d)-[:FROM_STATE]->(s))
        RETURN d
        '''
        with self.driver.session() as s:
            s.run(cypher, path=path, year=year, group=group, state=state)

    def subgraph_for_docs(self, paths: list[str]):
        cypher = '''
        MATCH (d:Document)
        WHERE d.path IN $paths
        OPTIONAL MATCH (d)-[r]-(n)
        RETURN d, r, n
        '''
        with self.driver.session() as s:
            return s.run(cypher, paths=paths).data()
