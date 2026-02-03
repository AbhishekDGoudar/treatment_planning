import streamlit as st
import fitz
import pandas as pd
from datetime import datetime
from core.extraction.extraction_utils import (
    extract_waiver_info, 
    extract_specific_sections, 
    process_logic_flags, 
    generate_doc_id,
    SECTIONS_TO_EXTRACT
)
from core.storage.graph_storage import upsert_document 

st.set_page_config(page_title="Waiver Multi-Ingest", layout="wide")
st.title("📂 Multi-File Waiver Extraction & Ingest")

if "processed_data" not in st.session_state:
    st.session_state.processed_data = []

# --- UPLOADER ---
st.subheader("Ingest Documents")
uploaded_files = st.file_uploader("Upload PDF waivers", type="pdf", accept_multiple_files=True)

col_btns_1, col_btns_2 = st.columns([1, 8])
with col_btns_1:
    process_btn = st.button("🚀 Process & Save")
with col_btns_2:
    if st.button("🗑️ Clear All"):
        st.session_state.processed_data = []
        st.rerun()

# --- PIPELINE ---
if process_btn:
    if uploaded_files:
        results = []
        with st.spinner(f"Processing {len(uploaded_files)} files..."):
            for uploaded_file in uploaded_files:
                file_bytes = uploaded_file.read()
                doc_id = generate_doc_id(file_bytes)
                
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                info = extract_waiver_info(doc)
                sections = extract_specific_sections(doc, SECTIONS_TO_EXTRACT)
                info.update(sections)
                info = process_logic_flags(info)
                info["File Name"] = uploaded_file.name
                
                # Neo4j Properties
                props = {
                    "doc_id": doc_id,
                    "state": info.get("State"),
                    "program_title": info.get("Program Title"),
                    "waiver_number": info.get("Application Number"),
                    "type_of_request": info.get("Application Type"),
                    "filename": uploaded_file.name,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "service_plan_safeguards_flag": info.get("Service_Plan_Safeguards_Flag")
                }

                try:
                    upsert_document(doc_id, props)
                except Exception as e:
                    st.error(f"Save Error: {e}")

                results.append(info)
                doc.close()
                
            st.session_state.processed_data = results
            st.success('''Extraction Completed !
                          Results saved !''')

st.divider()

# --- FULL PREVIEW TABLE ---
if st.session_state.processed_data:
    df = pd.DataFrame(st.session_state.processed_data)
    
    # All extracted columns shown here
    final_column_order = [
        "File Name", "Application Number", "State", "Program Title", 
        "Proposed Effective Date", "Approved Effective Date", 
        "Approved Effective Date of Waiver being Amended", "Application Type", 
        "B_1_b_Additional_Criteria", "Transition of Individuals Affected by Maximum Age Limitation", 
        "B_1_c_Transition_Plan", "Criminal History and/or Background Investigations", 
        "C_2_a_Criminal_History", "Service_Plan_Safeguards_Flag", "D_1_b_Service_Plan_Safeguards"
    ]
    df = df[[col for col in final_column_order if col in df.columns]]

    st.subheader("Global Extraction Table")
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Download Full CSV", data=csv, file_name="waiver_full_data.csv")

    st.divider()

    # --- UPDATED SIDE-BY-SIDE REVIEW ---
    st.subheader("Detailed Review")
    selected_filename = st.selectbox("Select file to inspect:", df["File Name"].tolist())
    
    if selected_filename:
        selected_row = next(item for item in st.session_state.processed_data if item["File Name"] == selected_filename)
        left, right = st.columns([1, 2])
        
        with left:
            st.markdown("#### Metadata Verification")
            st.write(f"**State:** {selected_row.get('State')}")
            st.write(f"**Application Number:** {selected_row.get('Application Number')}")
            st.write(f"**Program Title:** {selected_row.get('Program Title')}")
            st.write(f"**App Type:** {selected_row.get('Application Type')}")
            
            st.info(f"**Service Plan Safeguards:** {selected_row.get('Service_Plan_Safeguards_Flag')}")
            st.info(f"**Criminal Check:** {selected_row.get('Criminal History and/or Background Investigations')}")
            st.info(f"**Transition:** {selected_row.get('Transition of Individuals Affected by Maximum Age Limitation')}")

        with right:
            st.markdown("#### Section Content")
            sec = st.radio("Section:", options=list(SECTIONS_TO_EXTRACT.keys()), horizontal=True)
            st.text_area(label=sec, value=selected_row.get(sec, ""), height=400)
else:
    st.info("No data processed.")