import pandas as pd
from neo4j import GraphDatabase
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os

# Configuration
CENTRAL_NODE_NAME = "United States"

# 1. Define the Mapping of Excel Headers to Graph Properties
PROPERTY_MAP = {
    "Application Number": "application_number",
    "What is the name of the waiver (1B)?": "waiver_name",
    "Which state (1A)?": "state_name",
    "Approved Effective Date (1E)": "effective_date",
    "Approved Effective Date of Waiver being Amended (1E)": "amendment_date", # Note: Checks for non-breaking space
    "Is this an:": "application_type",
    "Minimum age for Eligibility (B-1a)": "min_age",
    "Maximum age for Eligibility (B-1a)": "max_age",
    "Individual cost limits in considering eligibility (B-2)": "cost_limits"
}

# 2. List of Columns to EXCLUDE from being created as Themes
EXCLUDE_FROM_THEMES = list(PROPERTY_MAP.keys()) + [
   # Add any specific columns you want to ignore completely here
]

class Command(BaseCommand):
    help = 'Wipes database and ingests waiver data from Excel into Neo4j: Country <-> State <-> WaiverApplication <-> Theme'

    # No add_arguments method needed as path is hardcoded

    def clean_database(self, session):
        """Wipes all nodes and relationships."""
        self.stdout.write(self.style.WARNING("⚠️  Deleting all existing nodes and relationships..."))
        session.run("MATCH (n) DETACH DELETE n")
        self.stdout.write(self.style.SUCCESS("✅ Database cleaned."))

    def load_data(self, file_path):
        """Loads Excel data."""
        self.stdout.write(f"Loading data from: {file_path}")
        
        if not os.path.exists(file_path):
             raise CommandError(f"File not found: {file_path}")

        try:
            # Using read_excel for .xlsx files. 
            # dtype=str prevents auto-conversion of IDs/Zipcodes to floats/ints
            df = pd.read_excel(file_path, dtype=str)
        except Exception as e:
            raise CommandError(f"Error reading Excel file: {e}")

        # Ensure required columns exist
        required = ["Application Number", "What is the name of the waiver (1B)?", "Which state (1A)?"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise CommandError(f"Missing required columns in Excel: {missing}")

        df = df.fillna('')
        return df

    def transform_row(self, row):
        """
        Transforms a Pandas row into a dictionary structure for Neo4j.
        Separates core properties from Themes.
        """
        # 1. Extract Core Properties
        app_props = {}
        for header, prop_name in PROPERTY_MAP.items():
            val = row.get(header, '')
            app_props[prop_name] = str(val).strip()

        # 2. Extract Themes
        themes = []
        for col_header, cell_value in row.items():
            # Skip excluded columns
            if col_header in EXCLUDE_FROM_THEMES:
                continue
            
            # Skip empty cells
            val_str = str(cell_value).strip()
            if not val_str or val_str.lower() == 'nan':
                continue

            themes.append({
                "name": str(col_header).strip(),
                "value": val_str
            })

        return {
            "props": app_props,
            "themes": themes
        }

    def ingest_to_neo4j(self, df):
        driver = None
        try:
            self.stdout.write(f"Connecting to Neo4j at {settings.NEO4J_URI}...")
            driver = GraphDatabase.driver(
                settings.NEO4J_URI, 
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
            )
            driver.verify_connectivity()

            with driver.session(database=settings.NEO4J_DATABASE) as session:
                
                # 1. Clean DB
                self.clean_database(session)

                # 2. Setup Constraints
                constraints = [
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Country) REQUIRE c.name IS UNIQUE;",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.name IS UNIQUE;",
                    "CREATE CONSTRAINT IF NOT EXISTS FOR (w:WaiverApplication) REQUIRE w.applicationNumber IS UNIQUE;"
                ]
                for c in constraints:
                    session.run(c)
                
                # 3. Create Country
                session.run("MERGE (c:Country {name: $name})", name=CENTRAL_NODE_NAME)

                # 4. Process Data in Batches
                batch_size = 100
                batch_data = []

                self.stdout.write(f"Processing {len(df)} rows...")
                
                for index, row in df.iterrows():
                    processed_row = self.transform_row(row)
                    
                    # Skip if no application number
                    if not processed_row['props']['application_number']:
                        continue

                    batch_data.append(processed_row)

                    if len(batch_data) >= batch_size:
                        self._write_batch(session, batch_data)
                        batch_data = []
                        self.stdout.write(f"Processed {index + 1} records...")

                # Write remaining
                if batch_data:
                    self._write_batch(session, batch_data)

            self.stdout.write(self.style.SUCCESS("\n✅ Ingestion completed successfully!"))

        except Exception as e:
            raise CommandError(f"Ingestion failed: {e}")
        finally:
            if driver:
                driver.close()

    def _write_batch(self, session, batch_data):
        """Runs the Cypher query for a batch of applications."""
        query = """
        UNWIND $batch AS data
        
        // 1. Create Structure: Country <-> State
        MERGE (country:Country {name: $country_name})
        MERGE (state:State {name: data.props.state_name})
        MERGE (state)-[:LOCATED_IN]->(country)
        MERGE (country)-[:HAS_STATE]->(state)

        // 2. Create WaiverApplication
        MERGE (app:WaiverApplication {applicationNumber: data.props.application_number})
        SET 
            app.waiverName = data.props.waiver_name,
            app.effectiveDate = data.props.effective_date,
            app.amendmentDate = data.props.amendment_date,
            app.type = data.props.application_type,
            app.minAge = data.props.min_age,
            app.maxAge = data.props.max_age,
            app.costLimits = data.props.cost_limits
        
        // 3. Link WaiverApplication <-> State
        MERGE (app)-[:SUBMITTED_BY]->(state)
        MERGE (state)-[:HAS_APPLICATION]->(app)

        // 4. Create Themes
        WITH app, data
        UNWIND data.themes AS themeData
            // Create a new Theme node for every entry
            CREATE (t:Theme)
            SET t.name = themeData.name,
                t.value = themeData.value
            
            // Link WaiverApplication <-> Theme (Bidirectional)
            CREATE (app)-[:HAS_THEME]->(t)
            CREATE (t)-[:BELONGS_TO]->(app)
        """
        session.run(query, batch=batch_data, country_name=CENTRAL_NODE_NAME)

    def handle(self, *args, **options):
        # Using the specific file variable requested
        file_name = getattr(settings, 'DATA_ROOT', '.') + "/SED Waiver Data - Treatment Planning.xlsx"
        
        # Check if settings.DATA_ROOT is defined, if not handle gracefully or rely on os.path
        if not hasattr(settings, 'DATA_ROOT'):
             self.stdout.write(self.style.WARNING("settings.DATA_ROOT not found, assuming current directory."))
             file_name = "SED Waiver Data - Treatment Planning.xlsx"

        df = self.load_data(file_name)
        self.ingest_to_neo4j(df)