import json
import re
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from core.rag.generator import GeneratorFactory, PromptPiece
from core.thematic.themes import Theme

ThemeCodings = Dict[str, Dict[str, Any]]  # theme_name -> {applies, confidence, evidence}
CodingResults = Dict[str, Dict[str, ThemeCodings]]  # waiver_id -> section -> ThemeCodings


def _build_coding_prompt(section_text: str, themes: List[Theme]) -> List[PromptPiece]:
    theme_list = "\n".join(
        f"{i + 1}. {t.name}: {t.description}"
        for i, t in enumerate(themes)
    )
    theme_names_json = json.dumps([t.name for t in themes])

    return [
        PromptPiece(
            role="system",
            content=(
                "You are a qualitative researcher performing MAXQDA-style thematic coding on "
                "Medicaid HCBS waiver policy text. Identify which themes are present in the "
                "given text and extract a supporting direct quote as evidence. "
                "Respond ONLY with valid JSON — no markdown fences, no explanation, no extra text."
            ),
        ),
        PromptPiece(
            role="user",
            content=(
                f"Analyze the following waiver section and code it against each theme.\n\n"
                f"THEMES:\n{theme_list}\n\n"
                f"TEXT:\n{section_text}\n\n"
                f"Return a JSON object with this exact structure (include ALL {len(themes)} themes):\n"
                f'{{"codings": [\n'
                f'  {{"theme": "<exact theme name>", "applies": true, "confidence": 0.85, "evidence": "<direct quote from text>"}},\n'
                f'  {{"theme": "<exact theme name>", "applies": false, "confidence": 0.0, "evidence": null}}\n'
                f']}}\n\n'
                f"Theme names MUST exactly match one of: {theme_names_json}\n"
                f"For themes not present: applies=false, confidence=0.0, evidence=null."
            ),
        ),
    ]


def _empty_codings(theme_names: List[str]) -> ThemeCodings:
    return {name: {"applies": False, "confidence": 0.0, "evidence": None} for name in theme_names}


def _parse_coding_response(response: str, theme_names: List[str]) -> ThemeCodings:
    empty = _empty_codings(theme_names)
    try:
        # Strip markdown code fences if model wraps output
        cleaned = re.sub(r"```(?:json)?", "", response).strip().rstrip("`")
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if not json_match:
            return empty

        data = json.loads(json_match.group())
        codings_list = data.get("codings", [])

        codings_map: ThemeCodings = {}
        for item in codings_list:
            name = item.get("theme", "")
            if name in theme_names:
                codings_map[name] = {
                    "applies": bool(item.get("applies", False)),
                    "confidence": min(1.0, max(0.0, float(item.get("confidence", 0.0)))),
                    "evidence": item.get("evidence") or None,
                }

        # Merge with empty defaults so every theme is always present
        return {**empty, **codings_map}

    except (json.JSONDecodeError, ValueError, TypeError):
        return empty


def code_section(
    section_text: str,
    themes: List[Theme],
    generator: GeneratorFactory,
) -> ThemeCodings:
    theme_names = [t.name for t in themes]
    if not section_text or section_text.strip() in ("", "Not Found", "nan"):
        return _empty_codings(theme_names)

    prompt = _build_coding_prompt(section_text, themes)
    response = generator.generate(prompt)
    return _parse_coding_response(response, theme_names)


def code_dataframe(
    df: pd.DataFrame,
    section_columns: List[str],
    themes: List[Theme],
    generator: GeneratorFactory,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> CodingResults:
    """
    Code every (waiver, section) pair in the dataframe.
    Returns: {waiver_id: {section_col: {theme: {applies, confidence, evidence}}}}
    """
    results: CodingResults = {}
    total = len(df) * len(section_columns)
    done = 0

    for idx, row in df.iterrows():
        waiver_id = str(row.get("Application Number", f"row_{idx}"))
        results[waiver_id] = {}

        for col in section_columns:
            raw = row.get(col, "")
            text = str(raw) if raw and str(raw) not in ("nan", "None") else ""
            results[waiver_id][col] = code_section(text, themes, generator)
            done += 1
            if progress_callback:
                progress_callback(done / total)

    return results
