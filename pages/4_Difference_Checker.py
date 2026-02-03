import streamlit as st
import pandas as pd
from difflib import HtmlDiff, SequenceMatcher
import re
import base64
from datetime import datetime

# ====== APP CONFIG ======
st.set_page_config(page_title="Waiver DiffChecker", layout="wide")
st.title("Waiver Document DiffChecker")
st.write("Compare two waiver records section by section (text columns only).")

st.markdown(
    """
    <div style="padding:10px;border-radius:8px;background:rgba(104, 240, 125, 0.4)">
        📘 For detailed instructions, visit the 
        <a href="https://github.com/chandan-00/Difference_check/blob/main/README.md#-step-1--upload-file" target="_blank">
        GitHub Repository</a>.
    </div>
    """,
    unsafe_allow_html=True
)


def generate_full_diff_report(diffs, metadata=None, title="Full Policy Diff Report"):
    """
    Create a single combined HTML document containing diffs for all compared columns.
    Includes metadata and a clickable Table of Contents.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Metadata section
    meta_section = ""
    if metadata:
        meta_rows = "".join(
            f"<tr><td><b>{key}</b></td><td>{val}</td></tr>" for key, val in metadata.items()
        )
        meta_section = f"""
        <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
            <tbody>{meta_rows}</tbody>
        </table>
        """

    # Generate table of contents
    toc_entries = ""
    for col in diffs.keys():
        section_id = col.replace(" ", "_").replace(".", "").replace("(", "").replace(")", "")
        toc_entries += f"<li><a href='#{section_id}'>{col}</a></li>"

    toc_html = f"""
    <div style="background-color:#2b2b2b;padding:10px 15px;border-radius:6px;margin-bottom:20px;">
        <h2 style="color:#61dafb;margin-top:0;">Table of Contents</h2>
        <ul style="list-style-type:none;margin:0;padding-left:10px;">
            {toc_entries}
        </ul>
    </div>
    """

    # Combine all column diffs into sections
    all_sections = ""
    for col, html in diffs.items():
        section_id = col.replace(" ", "_").replace(".", "").replace("(", "").replace(")", "")
        all_sections += f"""
        <h2 id="{section_id}" style="color:#61dafb;border-bottom:1px solid #444;padding-bottom:4px;margin-top:30px;">
            {col}
        </h2>
        <div class="diff-container">{html}</div>
        """

    # Full document structure
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            html {{
                scroll-behavior: smooth;
            }}
            body {{
                background-color: #1e1e1e;
                color: #f5f5f5;
                font-family: monospace;
                padding: 20px;
                line-height: 1.5;
            }}
            h1 {{
                font-size: 1.6em;
                color: #61dafb;
            }}
            h2 {{
                font-size: 1.2em;
            }}
            a {{
                color: #61dafb;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            table {{
                background-color: #2b2b2b;
                border: 1px solid #555;
                border-radius: 6px;
            }}
            td {{
                padding: 6px 10px;
                border-bottom: 1px solid #444;
            }}
            td:first-child {{
                width: 220px;
                color: #61dafb;
            }}
            .diff-container {{
                background-color: #1e1e1e;
                border-radius: 10px;
                padding: 10px;
                margin-top: 10px;
            }}
            ul li {{
                margin: 5px 0;
            }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <p><i>Generated on {timestamp}</i></p>
        {meta_section}
        {toc_html}
        {all_sections}
    </body>
    </html>
    """
    return html_content


def generate_html_report(diff_html, title="Diff Report"):
    """
    Wrap the diff HTML in a standalone HTML document for export.
    """
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{title}</title>
        <style>
            body {{
                background-color: #1e1e1e;
                color: white;
                font-family: monospace;
                padding: 20px;
            }}
            h1 {{
                color: #fff;
                font-size: 1.4em;
            }}
            a {{
                color: #61dafb;
            }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        {diff_html}
    </body>
    </html>
    """
    return html_content


def highlight_inline_diff(old_text, new_text):
    """
    Compare two text blocks and highlight sentence-level and word-level changes.
    - Light red/green: changed sentences
    - Dark red/green: changed words inside sentences
    """
    old_sentences = re.split(r'(?<=[.!?]) +', old_text)
    new_sentences = re.split(r'(?<=[.!?]) +', new_text)
    sm = SequenceMatcher(None, old_sentences, new_sentences)
    html_output = ""

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for sent in old_sentences[i1:i2]:
                html_output += f"<div>{sent}</div>"
        elif tag == 'replace':
            for o, n in zip(old_sentences[i1:i2], new_sentences[j1:j2]):
                inner_html = inline_word_diff(o, n)
                html_output += f"<div style='background-color:#2e7d3240;padding:6px;border-radius:6px;margin:2px 0'>{inner_html}</div>"
        elif tag == 'delete':
            for sent in old_sentences[i1:i2]:
                html_output += f"<div style='background-color:#c6282840;padding:6px;border-radius:6px;margin:2px 0'><span style='color:#c62828;'>{sent}</span></div>"
        elif tag == 'insert':
            for sent in new_sentences[j1:j2]:
                html_output += f"<div style='background-color:#2e7d3240;padding:6px;border-radius:6px;margin:2px 0'><span style='color:#2e7d32;'>{sent}</span></div>"

    return html_output


def inline_word_diff(old, new):
    """Highlight differences inside a sentence (dark green/red for added/removed words)."""
    sm = SequenceMatcher(None, old.split(), new.split())
    result = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            result.append(" ".join(new.split()[j1:j2]))
        elif tag == 'replace':
            result.append(
                f"<span style='background-color:#c62828;color:white;'>{' '.join(old.split()[i1:i2])}</span> "
                f"<span style='background-color:#2e7d32;color:white;'>{' '.join(new.split()[j1:j2])}</span>"
            )
        elif tag == 'delete':
            result.append(f"<span style='background-color:#c62828;color:white;'>{' '.join(old.split()[i1:i2])}</span>")
        elif tag == 'insert':
            result.append(f"<span style='background-color:#2e7d32;color:white;'>{' '.join(new.split()[j1:j2])}</span>")
    return " ".join(result)

def side_by_side_diff(text_a, text_b, app_a, app_b):
    """Generate an HTML table showing side-by-side differences with color."""
    differ = HtmlDiff(wrapcolumn=80)
    diff_html = differ.make_table(
        text_a.splitlines(),
        text_b.splitlines(),
        fromdesc=f"{app_a}",
        todesc=f"{app_b}",
        context=True,
        numlines=2
    )

    # Add dark theme CSS for readability
    custom_css = """
    <style>
    table.diff {width:100%; border-collapse: collapse; font-family: monospace; background-color:#1e1e1e; color:#ffffff;}
    td, th {padding:4px 8px;}
    td.diff_header {background-color:#333333; color:#ffffff;}
    .diff_add {background-color:#2e7d32; color:#ffffff;}
    .diff_chg {background-color:#1565c0; color:#ffffff;}
    .diff_sub {background-color:#c62828; color:#ffffff;}
    </style>
    """
    return custom_css + diff_html

def side_by_side_inline_diff(old_text, new_text):
    """
    Improved side-by-side diff:
    - Retains original text in each column.
    - Highlights removed parts (dark red) on the left.
    - Highlights added parts (dark green) on the right.
    - Uses light red/green backgrounds for changed sentences.
    """
    old_sentences = re.split(r'(?<=[.!?]) +', old_text)
    new_sentences = re.split(r'(?<=[.!?]) +', new_text)
    sm = SequenceMatcher(None, old_sentences, new_sentences)

    left_html, right_html = "", ""

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            # unchanged sentences
            for s in old_sentences[i1:i2]:
                left_html  += f"<div>{s}</div>"
            for s in new_sentences[j1:j2]:
                right_html += f"<div>{s}</div>"

        elif tag == "replace":
            # sentence has internal changes — word-level diff
            for o, n in zip(old_sentences[i1:i2], new_sentences[j1:j2]):
                matcher = SequenceMatcher(None, o.split(), n.split())
                left_sentence, right_sentence = "", ""

                for op, a1, a2, b1, b2 in matcher.get_opcodes():
                    if op == "equal":
                        left_sentence  += " " + " ".join(o.split()[a1:a2])
                        right_sentence += " " + " ".join(n.split()[b1:b2])
                    elif op == "delete":
                        removed = " ".join(o.split()[a1:a2])
                        left_sentence += f" <span style='color:#c62828;font-weight:bold'>{removed}</span>"
                    elif op == "insert":
                        added = " ".join(n.split()[b1:b2])
                        right_sentence += f" <span style='color:#2e7d32;font-weight:bold'>{added}</span>"
                    elif op == "replace":
                        removed = " ".join(o.split()[a1:a2])
                        added = " ".join(n.split()[b1:b2])
                        left_sentence  += f" <span style='color:#c62828;font-weight:bold'>{removed}</span>"
                        right_sentence += f" <span style='color:#2e7d32;font-weight:bold'>{added}</span>"

                left_html  += f"<div style='background-color:#c6282820;padding:6px;border-radius:6px;margin:2px 0'>{left_sentence.strip()}</div>"
                right_html += f"<div style='background-color:#2e7d3220;padding:6px;border-radius:6px;margin:2px 0'>{right_sentence.strip()}</div>"

        elif tag == "delete":
            # removed entire sentence(s)
            for s in old_sentences[i1:i2]:
                left_html  += f"<div style='background-color:#c6282820;padding:6px;border-radius:6px;margin:2px 0;color:#c62828'>{s}</div>"
            for _ in range(len(old_sentences[i1:i2])):
                right_html += "<div style='background-color:#2b2b2b;padding:6px;border-radius:6px;margin:2px 0'>&nbsp;</div>"

        elif tag == "insert":
            # added entire sentence(s)
            for _ in range(len(new_sentences[j1:j2])):
                left_html  += "<div style='background-color:#2b2b2b;padding:6px;border-radius:6px;margin:2px 0'>&nbsp;</div>"
            for s in new_sentences[j1:j2]:
                right_html += f"<div style='background-color:#2e7d3220;padding:6px;border-radius:6px;margin:2px 0;color:#2e7d32'>{s}</div>"

    combined_html = f"""
    <div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;background-color:#1e1e1e;
                color:white;font-family:monospace;border-radius:10px;padding:10px'>
        <div style='border-right:1px solid #555;padding-right:10px'>{left_html}</div>
        <div style='padding-left:10px'>{right_html}</div>
    </div>
    """
    return combined_html

# ====== FILE UPLOAD ======
uploaded_file = st.file_uploader("Upload Waiver Dataset (.xlsx)", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file, sheet_name="Data Master")

    # Filter only text columns (heuristic: long text or string dtype)
    text_cols = [
        c for c in df.columns
        if df[c].dtype == "object" and df[c].astype(str).str.len().mean() > 40
    ]

    st.success(f"Loaded {len(df)} records. Found {len(text_cols)} text-based columns for comparison.")

    # ====== SELECT RECORDS ======
    app_numbers = sorted(df["Application Number"].dropna().unique())
    col1, col2 = st.columns(2)
    app_a = col1.selectbox("Select Document A", app_numbers, key="docA")
    app_b = col2.selectbox("Select Document B", app_numbers, key="docB")

    # Select columns to compare
    selected_cols = st.multiselect(
        "Select sections (columns) to compare",
        text_cols,
        default=text_cols
    )

    # View mode toggle
    view_mode = st.radio("Select Diff View Mode:", ["Inline View", "Side-by-Side View"], horizontal=True)

    # ====== COMPARE BUTTON ======
    if st.button("🔍 Compare Documents"):
        doc_a = df[df["Application Number"] == app_a].iloc[0]
        doc_b = df[df["Application Number"] == app_b].iloc[0]

        changes_summary = []
        diff = HtmlDiff(wrapcolumn=80)

        st.markdown("---")
        st.header(f"Comparison: {app_a} 🆚 {app_b}")

        diffs = {}
        metadata = {
            "Document A": app_a,
            "Document B": app_b,
            "Comparison Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if app_a != app_b:
            if selected_cols:
                for col in selected_cols:
                    text_a = str(doc_a[col]) if pd.notna(doc_a[col]) else ""
                    text_b = str(doc_b[col]) if pd.notna(doc_b[col]) else ""

                    if text_a.strip() == text_b.strip():
                        continue  # skip unchanged sections
                        
                    if view_mode == "Inline View":
                        # Inline diff render
                        html_diff = highlight_inline_diff(text_a, text_b)

                        # Dark theme container
                        styled_html = f"""
                        <div style='background-color:#1e1e1e;color:white;padding:10px;border-radius:10px;font-family:monospace'>
                        {html_diff}
                        </div>
                        """
                        changes_summary.append(col)
                        diffs[col] = styled_html
                        with st.expander(f"🧩 {col}", expanded=False):
                            st.components.v1.html(styled_html, height=400, scrolling=True)
                            # Generate downloadable HTML file
                            html_report = generate_html_report(styled_html, title=f"Diff Report - {app_a} vs {app_b}")
                            b64 = base64.b64encode(html_report.encode()).decode()
                            href = f'<a href="data:text/html;base64,{b64}" download="Diff_Report_{app_a}_vs_{app_b}_{col}.html">📥 Download HTML Report</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        
                    else:
                        # Side-by-side display
                        # Generate true side-by-side diff table
                        styled_html = side_by_side_inline_diff(text_a, text_b)
                        changes_summary.append(col)
                        diffs[col] = styled_html
                        with st.expander(f"🧩 {col}", expanded=False):
                            st.components.v1.html(styled_html, height=400, scrolling=True)
                            # Generate downloadable HTML file
                            html_report = generate_html_report(styled_html, title=f"Diff Report - {app_a} vs {app_b}")
                            b64 = base64.b64encode(html_report.encode()).decode()
                            href = f'<a href="data:text/html;base64,{b64}" download="Diff_Report_{app_a}_vs_{app_b}_{col}.html">📥 Download HTML Report</a>'
                            st.markdown(href, unsafe_allow_html=True)
                
                    

                full_html = generate_full_diff_report(diffs, metadata, title="Full Policy Diff Report")
                b64 = base64.b64encode(full_html.encode()).decode()
                href = f'<a href="data:text/html;base64,{b64}" download="Full_Policy_Diff_Report.html">📥 Download Full Diff Report</a>'
                st.markdown(href, unsafe_allow_html=True)


                # ====== SUMMARY ====== 
                st.markdown("---")
                if changes_summary:
                    st.subheader("📊 Summary of Changed Sections")
                    st.write(f"{len(changes_summary)} out of {len(selected_cols)} text sections have changes:")
                    st.write(", ".join(changes_summary))
                else:
                    st.info("No differences found between the selected records.")
            else:
                st.warning("Please select at least one text section (column) to compare.")
        else:
            st.warning("Please select two different applications to compare.")

else:
    st.info("Please upload your Excel file to begin.")
