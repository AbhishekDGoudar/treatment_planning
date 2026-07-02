"""
Claude Sonnet 4.6 multi-label classifier for HCBS waiver themes.

Uses prompt caching on the static system prompt (theme definitions) so
repeated calls only pay full price for the user text, not the theme list.
"""
import json
import re
from typing import Callable, List, Optional

import anthropic
import pandas as pd

from core.thematic.themes import PREDEFINED_THEMES, Theme

MODEL = "claude-sonnet-4-6"
_SYSTEM_PROMPT_CACHE: dict[str, str] = {}


def build_system_prompt(themes: List[Theme]) -> str:
    cache_key = ",".join(t.name for t in themes)
    if cache_key in _SYSTEM_PROMPT_CACHE:
        return _SYSTEM_PROMPT_CACHE[cache_key]

    theme_lines = []
    for i, t in enumerate(themes, 1):
        theme_lines.append(f"{i}. {t.name}: {t.description}")
        theme_lines.append(f"   Keywords: {', '.join(t.keywords)}")

    theme_names_json = json.dumps([t.name for t in themes])

    prompt = "\n".join([
        "You are a qualitative researcher performing thematic analysis on Medicaid HCBS waiver policy text.",
        "Analyze the given text and classify it against every theme listed below.",
        "",
        "THEMES:",
        *theme_lines,
        "",
        "Return ONLY valid JSON — no markdown fences, no explanation:",
        '{"predictions": [',
        '  {"theme": "<exact theme name>", "confidence": 0.85, "applies": true},',
        '  {"theme": "<exact theme name>", "confidence": 0.0,  "applies": false}',
        "]}",
        "",
        f"Rules:",
        f"- Include ALL {len(themes)} themes in the output.",
        f"- Theme names must exactly match one of: {theme_names_json}",
        "- confidence: float 0.0–1.0 (certainty that the theme is present)",
        "- applies: true when the theme is clearly expressed in the text",
    ])

    _SYSTEM_PROMPT_CACHE[cache_key] = prompt
    return prompt


def _parse_response(raw: str, theme_names: List[str], threshold: float) -> pd.DataFrame:
    empty_rows = [{"Theme": n, "Confidence": 0.0, "Predicted": "No"} for n in theme_names]
    try:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if not m:
            return pd.DataFrame(empty_rows)

        data = json.loads(m.group())
        rows: dict[str, dict] = {}
        for p in data.get("predictions", []):
            name = p.get("theme", "")
            if name in theme_names:
                conf = float(p.get("confidence", 0.0))
                conf = min(1.0, max(0.0, conf))
                rows[name] = {
                    "Theme": name,
                    "Confidence": round(conf, 3),
                    "Predicted": "Yes" if conf >= threshold else "No",
                }

        result = [rows.get(n, {"Theme": n, "Confidence": 0.0, "Predicted": "No"}) for n in theme_names]
        df = pd.DataFrame(result).sort_values("Confidence", ascending=False).reset_index(drop=True)
        return df

    except (json.JSONDecodeError, ValueError, TypeError):
        return pd.DataFrame(empty_rows)


def classify_text(
    text: str,
    client: anthropic.Anthropic,
    themes: List[Theme] = None,
    threshold: float = 0.5,
    system_prompt: Optional[str] = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Classify a single text against all themes.

    Returns:
        (DataFrame[Theme, Confidence, Predicted], usage dict)
    """
    if themes is None:
        themes = PREDEFINED_THEMES
    if system_prompt is None:
        system_prompt = build_system_prompt(themes)

    theme_names = [t.name for t in themes]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=[{
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"Classify this waiver text against all {len(themes)} themes:\n\n{text}",
        }],
    )

    raw = next((b.text for b in response.content if b.type == "text"), "")
    df = _parse_response(raw, theme_names, threshold)

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0),
        "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0),
    }
    return df, usage


def classify_dataframe(
    df: pd.DataFrame,
    text_column: str,
    client: anthropic.Anthropic,
    id_column: str = "Application Number",
    themes: List[Theme] = None,
    threshold: float = 0.5,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Classify every row in a DataFrame.

    Returns:
        (results DataFrame, aggregated usage dict)
    """
    if themes is None:
        themes = PREDEFINED_THEMES

    system_prompt = build_system_prompt(themes)
    theme_names = [t.name for t in themes]

    total_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "calls": 0,
        "skipped": 0,
    }

    rows_out = []
    n = len(df)

    for i, (_, row) in enumerate(df.iterrows()):
        waiver_id = str(row.get(id_column, f"row_{i}"))
        text = str(row.get(text_column, ""))

        base = {"Waiver ID": waiver_id, "Column": text_column}

        if not text or text.strip() in ("", "nan", "None"):
            for name in theme_names:
                rows_out.append({**base, "Theme": name, "Confidence": 0.0, "Predicted": "No"})
            total_usage["skipped"] += 1
        else:
            pred_df, usage = classify_text(text, client, themes, threshold, system_prompt)
            for _, pred_row in pred_df.iterrows():
                rows_out.append({**base, **pred_row.to_dict()})
            for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
                total_usage[k] += usage.get(k, 0)
            total_usage["calls"] += 1

        if progress_callback:
            progress_callback(i + 1, n)

    return pd.DataFrame(rows_out), total_usage


def estimate_cost(
    num_texts: int,
    avg_chars: int,
    num_themes: int = 20,
) -> dict:
    """Rough cost estimate before running a batch."""
    # tokens: ~4 chars per token
    system_tokens = 100 + num_themes * 40       # task description + theme definitions
    input_text_tokens = avg_chars // 4
    output_tokens = num_themes * 18             # ~18 tokens per theme in JSON

    # Sonnet 4.6 pricing (per million tokens)
    INPUT_PRICE = 3.00 / 1_000_000
    OUTPUT_PRICE = 15.00 / 1_000_000
    CACHE_WRITE_PRICE = 3.75 / 1_000_000
    CACHE_READ_PRICE = 0.30 / 1_000_000

    # First call: cache write; remaining: cache read
    first_call = (
        system_tokens * CACHE_WRITE_PRICE
        + input_text_tokens * INPUT_PRICE
        + output_tokens * OUTPUT_PRICE
    )
    subsequent_call = (
        system_tokens * CACHE_READ_PRICE
        + input_text_tokens * INPUT_PRICE
        + output_tokens * OUTPUT_PRICE
    )

    if num_texts <= 1:
        total = first_call
    else:
        total = first_call + (num_texts - 1) * subsequent_call

    return {
        "total_usd": round(total, 4),
        "per_call_usd": round(subsequent_call, 5),
        "estimated_seconds_sequential": round(num_texts * 6, 0),
        "system_tokens": system_tokens,
        "avg_input_text_tokens": input_text_tokens,
        "avg_output_tokens": output_tokens,
    }
