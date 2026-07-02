"""RAG-augmented code predictor using Claude API with prompt caching.

Given a text span and few-shot examples retrieved from the coded-segments
knowledge base, calls Claude to predict which codes from the 75-code
codebook apply.
"""
import json
import re
from functools import lru_cache
from typing import Callable

import anthropic
import pandas as pd

from core import config

# Codes colored #2364a2 in the codebook are section-identifier labels
# (e.g. "Application Number", "Which state (1A)?"). They are not
# interpretive themes and should be excluded from the prediction target set.
_SECTION_LABEL_COLOR = "#2364a2"


def load_codebook(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def theme_codes(df: pd.DataFrame) -> list[dict]:
    """Return only the interpretive theme codes (non-section-label rows)."""
    return (
        df[df["color"] != _SECTION_LABEL_COLOR][["guid", "name", "path", "color"]]
        .to_dict("records")
    )


@lru_cache(maxsize=4)
def build_system_prompt(codebook_path: str) -> str:
    """Build and cache the system prompt containing the full codebook.

    Cached by path so repeated calls within a session hit the cache.
    The prompt is also sent with cache_control: ephemeral so the API
    caches it server-side after the first call.
    """
    df = load_codebook(codebook_path)
    codes = theme_codes(df)
    code_list = "\n".join(
        f'- "{c["name"]}" | hierarchy: {c["path"]}' for c in codes
    )
    return (
        "You are a qualitative research coder trained to apply a structured "
        "codebook to text segments from Medicaid HCBS waiver policy documents.\n\n"
        "## Codebook (interpretive theme codes only)\n"
        f"{code_list}\n\n"
        "## Task\n"
        "You will be given:\n"
        "1. Retrieved examples — real text spans already coded by human researchers, "
        "with their assigned codes and similarity scores to the target text.\n"
        "2. The target text — a new span to code.\n\n"
        "Return ONLY a JSON array of predicted codes:\n"
        '[{"code": "<exact name from codebook>", "confidence": <0.0-1.0>, '
        '"rationale": "<one sentence citing evidence in the text>"}]\n\n'
        "Rules:\n"
        "- Use only code names that appear verbatim in the codebook above.\n"
        "- Include every code that has genuine supporting evidence in the target text.\n"
        "- Confidence ≥ 0.7 means strong, direct textual evidence.\n"
        "- Base predictions on the target text; use examples as reference context only.\n"
        "- Return an empty array [] if no codes apply."
    )


def predict_codes(
    text: str,
    examples: list[dict],
    client: anthropic.Anthropic,
    codebook_path: str,
    threshold: float = 0.5,
) -> tuple[list[dict], dict]:
    """Predict codes for a text span using retrieved examples as few-shot context.

    Returns (predictions_above_threshold, usage_dict).
    """
    system_prompt = build_system_prompt(codebook_path)

    example_blocks = []
    for i, ex in enumerate(examples, 1):
        snippet = ex["text"][:300].replace('"', '\\"')
        example_blocks.append(
            f"[{i}] Similarity: {ex['score']:.3f}\n"
            f"     Code: {ex['code']}\n"
            f"     Text: \"{snippet}\""
        )
    examples_section = (
        "\n\n".join(example_blocks) if example_blocks else "No examples retrieved."
    )

    user_message = (
        f"## Retrieved Examples from Knowledge Base\n\n"
        f"{examples_section}\n\n"
        f"## Target Text to Code\n\n"
        f'"{text}"'
    )

    response = client.messages.create(
        model=config.ANTHROPIC_LLM_MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(
            response.usage, "cache_creation_input_tokens", 0
        ),
        "cache_read_input_tokens": getattr(
            response.usage, "cache_read_input_tokens", 0
        ),
    }

    raw = response.content[0].text.strip()
    usage["raw_response"] = raw

    # Greedy match: captures the full outer array even if rationale strings contain ']'
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return [], usage

    try:
        predictions = json.loads(match.group())
    except json.JSONDecodeError:
        return [], usage

    return [p for p in predictions if p.get("confidence", 0) >= threshold], usage


def predict_codes_dataframe(
    df: pd.DataFrame,
    text_column: str,
    client: anthropic.Anthropic,
    codebook_path: str,
    store,
    id_column: str | None = "Application Number",
    k: int = 5,
    threshold: float = 0.5,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Run RAG coding on every row of df[text_column].

    Returns (results_df, total_usage_dict).
    results_df columns: id_column (if present), Row, Column, Code, Confidence, Rationale
    """
    from core.rag.kb_indexer import retrieve_examples

    rows = []
    total_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "calls": 0,
        "last_raw_response": "",
    }

    for i, (idx, row) in enumerate(df.iterrows()):
        text = str(row[text_column]) if pd.notna(row.get(text_column)) else ""
        if not text.strip():
            if progress_callback:
                progress_callback(i + 1, len(df))
            continue

        examples = retrieve_examples(text, store, k=k)
        preds, usage = predict_codes(
            text=text,
            examples=examples,
            client=client,
            codebook_path=codebook_path,
            threshold=threshold,
        )

        for key in ("input_tokens", "output_tokens",
                    "cache_creation_input_tokens", "cache_read_input_tokens"):
            total_usage[key] += usage[key]
        total_usage["calls"] += 1
        total_usage["last_raw_response"] = usage.get("raw_response", "")

        row_id = row.get(id_column, idx) if id_column else idx
        for pred in preds:
            rows.append({
                **({"ID": row_id} if id_column else {"Row": idx}),
                "Column": text_column,
                "Code": pred.get("code", ""),
                "Confidence": round(pred.get("confidence", 0), 3),
                "Rationale": pred.get("rationale", ""),
            })

        if progress_callback:
            progress_callback(i + 1, len(df))

    results_df = pd.DataFrame(rows)
    return results_df, total_usage
