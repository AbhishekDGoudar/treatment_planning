from typing import Any, Dict, List

import pandas as pd

CodingResults = Dict[str, Dict[str, Dict[str, Dict[str, Any]]]]


def build_waiver_theme_matrix(results: CodingResults, theme_names: List[str]) -> pd.DataFrame:
    """
    Rows = waivers, columns = themes.
    Cell value = max confidence for that theme across all sections of that waiver.
    """
    rows = []
    for waiver_id, sections in results.items():
        row: Dict[str, Any] = {"Waiver": waiver_id}
        for theme in theme_names:
            confs = [
                sections[sec][theme]["confidence"]
                for sec in sections
                if theme in sections.get(sec, {})
            ]
            row[theme] = round(max(confs), 3) if confs else 0.0
        rows.append(row)
    return pd.DataFrame(rows).set_index("Waiver")


def build_section_theme_matrix(
    results: CodingResults, waiver_id: str, theme_names: List[str]
) -> pd.DataFrame:
    """
    Rows = sections, columns = themes, values = confidence — for a single waiver.
    """
    if waiver_id not in results:
        return pd.DataFrame()
    rows = []
    for section, codings in results[waiver_id].items():
        row: Dict[str, Any] = {"Section": section}
        for theme in theme_names:
            row[theme] = round(codings.get(theme, {}).get("confidence", 0.0), 3)
        rows.append(row)
    return pd.DataFrame(rows).set_index("Section")


def get_evidence(
    results: CodingResults, waiver_id: str, theme: str
) -> List[Dict[str, Any]]:
    """
    All evidence quotes for a given theme across all sections of a waiver,
    sorted by descending confidence.
    """
    if waiver_id not in results:
        return []
    out = []
    for section, codings in results[waiver_id].items():
        c = codings.get(theme, {})
        if c.get("applies") and c.get("evidence"):
            out.append(
                {
                    "section": section,
                    "evidence": c["evidence"],
                    "confidence": c.get("confidence", 0.0),
                }
            )
    return sorted(out, key=lambda x: x["confidence"], reverse=True)


def build_labeled_dataset(
    results: CodingResults,
    df: pd.DataFrame,
    section_columns: List[str],
    theme_names: List[str],
) -> pd.DataFrame:
    """
    Flat export: one row per (waiver, section) with the raw text and binary columns
    per theme. Used as silver-label training data for text classification models.
    """
    text_lookup: Dict[str, Any] = {
        str(row.get("Application Number", idx)): row
        for idx, row in df.iterrows()
    }

    rows = []
    for waiver_id, sections in results.items():
        source_row = text_lookup.get(waiver_id, {})
        for col in section_columns:
            if col not in sections:
                continue
            codings = sections[col]
            text = str(source_row.get(col, "")) if source_row is not None else ""
            applied = [t for t in theme_names if codings.get(t, {}).get("applies")]
            row: Dict[str, Any] = {
                "waiver_id": waiver_id,
                "section": col,
                "text": text,
                "themes": "|".join(applied),
            }
            for theme in theme_names:
                row[theme] = int(codings.get(theme, {}).get("applies", False))
            rows.append(row)

    return pd.DataFrame(rows)
