import fitz  # PyMuPDF
from datetime import datetime
import re

def convert_date_format(date_str):
    """
    Convert date string to YYYY-MM-DD format.
    Accepts mm/dd/yy or mm/dd/yyyy, trims whitespace.
    """
    date_str = date_str.strip()
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""

from datetime import datetime
from typing import Optional

def parse_effective_date(date_str: str) -> Optional[datetime.date]:
    """
    Convert a date string to a datetime.date object.

    Accepts strings in the following formats:
        - 'YYYY-MM-DD' (e.g., '2025-11-13')
        - 'MM/DD/YY' (e.g., '11/13/25')
        - 'MM/DD/YYYY' (e.g., '11/13/2025')

    Returns None if the string is None, empty, or invalid.
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # If none of the formats matched, return None
    return None

def normalize_text(text):
    """
    Remove extra spaces and convert to lowercase for consistent matching.
    """
    return re.sub(r'\s+', ' ', text).strip().lower()

def extract_waiver_info(pdf_path):
    doc = fitz.open(pdf_path)
    results = {
        "State": "",
        "Program Title": "",
        "Waiver Number": "",
        "Amendment Number": "",
        "Draft ID": "",
        "Type of Request": "",
        "Requested Approval Period": "",
        "Type of Waiver": "",
        "Proposed Effective Date of Waiver being Amended": "",
        "Approved Effective Date of Waiver being Amended": "",
        "Approved Effective Date": "",
        "PRA Disclosure Statement": ""
    }

    for page in doc:
        text = page.get_text("text")
        lines = text.split('\n')

        for i, line in enumerate(lines):
            norm_line = normalize_text(line)

            # State (case and spacing insensitive)
            if "the state of" in norm_line and "requests approval" in norm_line and not results["State"]:
                match = re.search(r"the state of\s+(.*?)\s+requests approval", line, re.IGNORECASE)
                if match:
                    results["State"] = match.group(1).strip()

            # Program Title
            if "program title" in norm_line and not results["Program Title"]:
                # Try to get value on the same line after colon
                value = line.split(":", 1)[-1].strip()
                if not value:
                    # If empty, check subsequent lines until a line starting with a single uppercase letter and dot (C., D., etc.)
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j].strip()
                        if re.match(r"^[A-Z]\.$", next_line):
                            break
                        if next_line:
                            value += " " + next_line
                results["Program Title"] = value.strip()

            # Waiver Number (from header line)
            match = re.match(
                r"Application for 1915\(c\)\s*HCBS\s*Waiver\s*:\s*(?P<waiver_number>[\w\.]+)\s*-\s*(?P<date>.+)",
                line,
                re.IGNORECASE
            )
            if match and not results["Waiver Number"]:
                results["Waiver Number"] = match.group("waiver_number").strip()

            # Amendment Number
            if "amendment number" in norm_line and not results["Amendment Number"]:
                parts = re.split(r':', line, maxsplit=1)
                if len(parts) > 1:
                    results["Amendment Number"] = parts[1].strip()
                    if not results["Waiver Number"]:
                        results["Waiver Number"] = results["Amendment Number"]

            # Draft ID
            if "draft id" in norm_line and not results["Draft ID"]:
                parts = re.split(r':', line, maxsplit=1)
                if len(parts) > 1:
                    results["Draft ID"] = parts[1].strip()

            # Type of Request
            if "type of request" in norm_line and not results["Type of Request"]:
                parts = re.split(r':', line, maxsplit=1)
                if len(parts) > 1:
                    results["Type of Request"] = parts[1].strip()

            # Requested Approval Period (checkbox detection)
            if "requested approval period" in norm_line and not results["Requested Approval Period"]:
                for j in range(i + 1, min(i + 5, len(lines))):
                    sub_line = normalize_text(lines[j])
                    if "3 years" in sub_line and any(x in sub_line for x in ["☑", "✔", "x", "[x]"]):
                        results["Requested Approval Period"] = "3 years"
                        break
                    elif "5 years" in sub_line and any(x in sub_line for x in ["☑", "✔", "x", "[x]"]):
                        results["Requested Approval Period"] = "5 years"
                        break

            # Type of Waiver
            if "type of waiver" in norm_line and not results["Type of Waiver"]:
                for j in range(i + 1, min(i + 4, len(lines))):
                    if "regular waiver" in normalize_text(lines[j]):
                        results["Type of Waiver"] = "Regular Waiver"
                        break

            # Proposed Effective Date
            if "proposed effective date" in norm_line and not results["Proposed Effective Date of Waiver being Amended"]:
                date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", line)
                if date_match:
                    results["Proposed Effective Date of Waiver being Amended"] = convert_date_format(date_match.group(1))

            # Approved Effective Date
            if "approved effective date" in norm_line:
                date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", line)
                if date_match:
                    date_val = convert_date_format(date_match.group(1))
                    if "of waiver being amended" in norm_line:
                        # Only set if not already set or is different
                        if not results["Approved Effective Date of Waiver being Amended"] or results["Approved Effective Date of Waiver being Amended"] != date_val:
                            results["Approved Effective Date of Waiver being Amended"] = date_val
                    else:
                        if not results.get("Approved Effective Date") or results.get("Approved Effective Date") != date_val:
                            results["Approved Effective Date"] = date_val

            # PRA Disclosure Statement
            if "pra disclosure statement" in norm_line and not results["PRA Disclosure Statement"]:
                results["PRA Disclosure Statement"] = "Present"

    return results
