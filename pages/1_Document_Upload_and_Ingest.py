import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from core import config
from core.storage.graph_storage import count_documents, list_documents, upsert_document
from core.ui.sidebar import render_sidebar_settings
from core.extraction.extraction_utils import extract_waiver_info, parse_effective_date


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def _build_upload_path(state: str, waiver_number: str, approved_date, filename: str) -> Path:
    ext = Path(filename).suffix or ".pdf"
    state_folder = state or "unknown_state"
    waiver_name = _slugify(waiver_number) if waiver_number else "unknown_waiver"
    date_part = approved_date.strftime("%Y-%m-%d") if approved_date else "no_date"
    new_filename = f"{waiver_name}_{date_part}{ext}".upper()
    return config.UPLOADS_DIR / state_folder / new_filename


def _hash_bytes(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


st.set_page_config(page_title="Document Upload and Ingest", layout="wide")
st.title("Document Upload and Ingest")

render_sidebar_settings()

DEFAULT_ENTITY_MAP = {
    "State": "state",
    "Program Title": "program_title",
    "Waiver Number": "waiver_number",
    "Amendment Number": "amendment_number",
    "Draft ID": "draft_id",
    "Type of Request": "type_of_request",
    "Requested Approval Period": "requested_approval_period",
    "Type of Waiver": "type_of_waiver",
    "Proposed Effective Date of Waiver being Amended": "proposed_effective_date",
    "Approved Effective Date of Waiver being Amended": "amended_effective_date",
    "Approved Effective Date": "approved_effective_date",
    "PRA Disclosure Statement": "pra_disclosure_statement",
}

st.subheader("Upload a Single PDF")
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"], accept_multiple_files=False)

entity_map_text = st.text_area(
    "Entity map (JSON: extracted key -> Neo4j property)",
    value=json.dumps(DEFAULT_ENTITY_MAP, indent=2),
    height=200,
)

if uploaded_file is not None:
    content = uploaded_file.getvalue()
    doc_id = _hash_bytes(content)
    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = config.UPLOADS_DIR / f"{doc_id}.pdf"
    tmp_path.write_bytes(content)

    with st.spinner("Extracting metadata..."):
        extracted = extract_waiver_info(str(tmp_path))

    st.markdown("### Validate and Edit Metadata")
    try:
        entity_map = json.loads(entity_map_text)
    except json.JSONDecodeError:
        st.error("Entity map is not valid JSON.")
        entity_map = DEFAULT_ENTITY_MAP

    edited = {}
    with st.form("metadata_form"):
        for src_key, dest_key in entity_map.items():
            value = extracted.get(src_key, "")
            edited[dest_key] = st.text_input(f"{src_key} → {dest_key}", value=value)

        custom_notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Save to Neo4j")

    if submitted:
        approved_date = parse_effective_date(edited.get("approved_effective_date", "") or "")
        stored_path = _build_upload_path(
            edited.get("state", ""),
            edited.get("waiver_number", ""),
            approved_date,
            uploaded_file.name,
        )
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_path), stored_path)

        extra = {
            k: v for k, v in extracted.items() if k not in entity_map
        }

        props = dict(edited)
        props.update(
            {
                "doc_id": doc_id,
                "filename": uploaded_file.name,
                "stored_path": str(stored_path.relative_to(config.BASE_DIR)),
                "uploaded_at": datetime.utcnow().isoformat(),
                "notes": custom_notes,
                "extra_json": json.dumps(extra),
            }
        )

        try:
            upsert_document(doc_id, props)
            st.success("Saved to Neo4j.")
        except Exception as exc:
            st.error(f"Failed to save to Neo4j: {exc}")

st.divider()
st.subheader("Documents")

page_size = st.selectbox("Page size", [5, 10, 20], index=1)
total_docs = count_documents()
total_pages = max((total_docs + page_size - 1) // page_size, 1)
page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)

try:
    docs = list_documents(page=page, page_size=page_size)
    st.caption(f"Total documents: {total_docs}")
    if docs:
        st.json(docs)
    else:
        st.info("No documents found yet.")
except Exception as exc:
    st.error(f"Failed to load documents: {exc}")
