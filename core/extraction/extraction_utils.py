# import re
# from datetime import datetime
# from typing import Optional

# import fitz  # PyMuPDF


# def convert_date_format(date_str: str) -> str:
#     """
#     Convert date string to YYYY-MM-DD format.
#     Accepts mm/dd/yy or mm/dd/yyyy, trims whitespace.
#     """
#     date_str = date_str.strip()
#     for fmt in ("%m/%d/%y", "%m/%d/%Y"):
#         try:
#             return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
#         except ValueError:
#             continue
#     return ""


# def parse_effective_date(date_str: str) -> Optional[datetime.date]:
#     """
#     Convert a date string to a datetime.date object.

#     Accepts strings in the following formats:
#         - 'YYYY-MM-DD' (e.g., '2025-11-13')
#         - 'MM/DD/YY' (e.g., '11/13/25')
#         - 'MM/DD/YYYY' (e.g., '11/13/2025')

#     Returns None if the string is None, empty, or invalid.
#     """
#     if not date_str:
#         return None

#     date_str = date_str.strip()
#     for fmt in ("%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
#         try:
#             return datetime.strptime(date_str, fmt).date()
#         except ValueError:
#             continue

#     return None


# def normalize_text(text: str) -> str:
#     """
#     Remove extra spaces and convert to lowercase for consistent matching.
#     """
#     return re.sub(r"\s+", " ", text).strip().lower()


# def extract_waiver_info(pdf_path: str) -> dict:
#     doc = fitz.open(pdf_path)
#     results = {
#         "State": "",
#         "Program Title": "",
#         "Waiver Number": "",
#         "Amendment Number": "",
#         "Draft ID": "",
#         "Type of Request": "",
#         "Requested Approval Period": "",
#         "Type of Waiver": "",
#         "Proposed Effective Date of Waiver being Amended": "",
#         "Approved Effective Date of Waiver being Amended": "",
#         "Approved Effective Date": "",
#         "PRA Disclosure Statement": "",
#     }

#     for page in doc:
#         text = page.get_text("text")
#         lines = text.split("\n")

#         for i, line in enumerate(lines):
#             norm_line = normalize_text(line)

#             if "the state of" in norm_line and "requests approval" in norm_line and not results["State"]:
#                 match = re.search(r"the state of\s+(.*?)\s+requests approval", line, re.IGNORECASE)
#                 if match:
#                     results["State"] = match.group(1).strip()

#             if "program title" in norm_line and not results["Program Title"]:
#                 value = line.split(":", 1)[-1].strip()
#                 if not value:
#                     for j in range(i + 1, len(lines)):
#                         next_line = lines[j].strip()
#                         if re.match(r"^[A-Z]\.$", next_line):
#                             break
#                         if next_line:
#                             value += " " + next_line
#                 results["Program Title"] = value.strip()

#             match = re.match(
#                 r"Application for 1915\(c\)\s*HCBS\s*Waiver\s*:\s*(?P<waiver_number>[\w\.]+)\s*-\s*(?P<date>.+)",
#                 line,
#                 re.IGNORECASE,
#             )
#             if match and not results["Waiver Number"]:
#                 results["Waiver Number"] = match.group("waiver_number").strip()

#             if "amendment number" in norm_line and not results["Amendment Number"]:
#                 parts = re.split(r":", line, maxsplit=1)
#                 if len(parts) > 1:
#                     results["Amendment Number"] = parts[1].strip()
#                     if not results["Waiver Number"]:
#                         results["Waiver Number"] = results["Amendment Number"]

#             if "draft id" in norm_line and not results["Draft ID"]:
#                 parts = re.split(r":", line, maxsplit=1)
#                 if len(parts) > 1:
#                     results["Draft ID"] = parts[1].strip()

#             if "type of request" in norm_line and not results["Type of Request"]:
#                 parts = re.split(r":", line, maxsplit=1)
#                 if len(parts) > 1:
#                     results["Type of Request"] = parts[1].strip()

#             if "requested approval period" in norm_line and not results["Requested Approval Period"]:
#                 for j in range(i + 1, min(i + 5, len(lines))):
#                     sub_line = normalize_text(lines[j])
#                     if "3 years" in sub_line and any(x in sub_line for x in ["☑", "✔", "x", "[x]"]):
#                         results["Requested Approval Period"] = "3 years"
#                         break
#                     if "5 years" in sub_line and any(x in sub_line for x in ["☑", "✔", "x", "[x]"]):
#                         results["Requested Approval Period"] = "5 years"
#                         break

#             if "type of waiver" in norm_line and not results["Type of Waiver"]:
#                 for j in range(i + 1, min(i + 4, len(lines))):
#                     if "regular waiver" in normalize_text(lines[j]):
#                         results["Type of Waiver"] = "Regular Waiver"
#                         break

#             if "proposed effective date" in norm_line and not results["Proposed Effective Date of Waiver being Amended"]:
#                 date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", line)
#                 if date_match:
#                     results["Proposed Effective Date of Waiver being Amended"] = convert_date_format(
#                         date_match.group(1)
#                     )

#             if "approved effective date" in norm_line:
#                 date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", line)
#                 if date_match:
#                     date_val = convert_date_format(date_match.group(1))
#                     if "of waiver being amended" in norm_line:
#                         if not results["Approved Effective Date of Waiver being Amended"] or (
#                             results["Approved Effective Date of Waiver being Amended"] != date_val
#                         ):
#                             results["Approved Effective Date of Waiver being Amended"] = date_val
#                     else:
#                         if not results.get("Approved Effective Date") or results.get("Approved Effective Date") != date_val:
#                             results["Approved Effective Date"] = date_val

#             if "pra disclosure statement" in norm_line and not results["PRA Disclosure Statement"]:
#                 results["PRA Disclosure Statement"] = "Present"

#     return results



import re
import fitz  # PyMuPDF
import hashlib
from datetime import datetime
from typing import Dict, Any

# --- CONFIGURATION ---
SECTIONS_TO_EXTRACT = {
    "B_1_b_Additional_Criteria": {
        "start_anchor": "Additional Criteria. The state further specifies its target group(s) as follows:",
        "stop_anchor": "Transition of Individuals Affected by Maximum Age Limitation",
        "content_after": None 
    },
    "B_1_c_Transition_Plan": {
        "start_anchor": "Transition of Individuals Affected by Maximum Age Limitation",
        "stop_anchor": "Appendix B: Participant Access and Eligibility",
        "content_after": "Specify:" 
    },
    "C_2_a_Criminal_History": {
        "start_anchor": "Criminal History and/or Background Investigations",
        "stop_anchor": "Abuse Registry Screening",
        "content_after": "operating agency (if applicable):" 
    },
    "D_1_b_Service_Plan_Safeguards": {
        "start_anchor": "Service Plan Development Safeguards. Select one:",
        "stop_anchor": "Appendix D: Participant-Centered Planning and Service Delivery",
        "content_after": "Specify:" 
    }
}

def generate_doc_id(content: bytes) -> str:
    """Generates a unique hash for the file content."""
    return hashlib.md5(content).hexdigest()

def extract_waiver_info(doc: fitz.Document) -> Dict[str, str]:
    """Extracts general metadata from the first few pages of the PDF."""
    text = ""
    for page_num in range(min(3, len(doc))):
        text += doc.load_page(page_num).get_text("text")
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s{2,}", " ", text)
    
    results = {}
    
    state_match = re.search(r"The State of\s+([A-Za-z\s]+?)\s+requests approval", text, re.IGNORECASE)
    results["State"] = state_match.group(1).strip() if state_match else "Not Found"
    
    program_match = re.search(r"Program Title.*?:\s*([\s\S]+?)(?:Type of Request|Application for|Approved Effective|Proposed Effective|$)", text, re.IGNORECASE)
    results["Program Title"] = program_match.group(1).strip() if program_match else "Not Found"

    date_pattern = r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}|[A-Za-z]+\s+\d{1,2},\s*\d{2,4})"
    
    prop_match = re.search(rf"Proposed\s*Effective\s*Date\s*[:\-\–—]?\s*{date_pattern}", text, re.IGNORECASE)
    results["Proposed Effective Date"] = prop_match.group(1).strip() if prop_match else "Not Found"

    app_date_match = re.search(rf"Approved\s*Effective\s*Date\s*[:\-\–—]?\s*{date_pattern}", text, re.IGNORECASE)
    results["Approved Effective Date"] = app_date_match.group(1).strip() if app_date_match else "Not Found"

    amended_match = re.search(rf"Approved\s*Effective\s*Date\s*of\s*Waiver\s*being\s*Amended\s*[:\-\–—]?\s*{date_pattern}", text, re.IGNORECASE)
    results["Approved Effective Date of Waiver being Amended"] = amended_match.group(1).strip() if amended_match else "Not Found"

    app_type = "Not Found"
    if re.search(r"Request for an Amendment", text, re.IGNORECASE): app_type = "Amendment"
    elif re.search(r"Request for a Renewal", text, re.IGNORECASE): app_type = "Renewal"
    elif re.search(r"Application for a §1915\(c\)", text, re.IGNORECASE): app_type = "New"
    results["Application Type"] = app_type

    app_num_match = re.search(r"Application for 1915\(c\).*?:\s*([A-Z]{2}\.\d+\.R\d+\.\d+)", text, re.IGNORECASE)
    results["Application Number"] = app_num_match.group(1).strip() if app_num_match else "Not Found"
    
    return results

def extract_specific_sections(doc: fitz.Document, sections_config: Dict[str, Any]) -> Dict[str, str]:
    file_results = {}
    current_section_key = None
    ready_to_capture = False
    current_capture_list = []

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("blocks")
        for block in blocks:
            block_text = " ".join(block[4].strip().split())
            if current_section_key:
                if sections_config[current_section_key]["stop_anchor"] in block_text:
                    file_results[current_section_key] = "\n".join(current_capture_list)
                    current_section_key, ready_to_capture, current_capture_list = None, False, []

            if not current_section_key:
                for section_key, config in sections_config.items():
                    if config["start_anchor"] in block_text:
                        current_section_key, current_capture_list = section_key, []
                        ready_to_capture = config["content_after"] is None
                        break
                if current_section_key: continue

            if current_section_key and not ready_to_capture:
                if sections_config[current_section_key]["content_after"] in block_text:
                    ready_to_capture = True
                    continue

            if current_section_key and ready_to_capture and block_text:
                current_capture_list.append(block_text)

    for key in sections_config.keys():
        if key not in file_results: file_results[key] = "Not Found"
    return file_results

def process_logic_flags(data: Dict[str, Any]) -> Dict[str, Any]:
    data["Transition of Individuals Affected by Maximum Age Limitation"] = (
        "Not applicable. There is no maximum age limit" 
        if len(data.get("B_1_c_Transition_Plan", "")) < 15 
        else "Planning procedures are employed"
    )
    data["Criminal History and/or Background Investigations"] = (
        "Yes" if len(data.get("C_2_a_Criminal_History", "")) >= 15 else "No"
    )
    data["Service_Plan_Safeguards_Flag"] = (
        "Individuals may provide waiver." 
        if len(data.get("D_1_b_Service_Plan_Safeguards", "")) >= 15 
        else "Individuals may not provide waiver."
    )
    return data