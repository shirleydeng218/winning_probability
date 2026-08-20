import hashlib
import json
import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests

from winprob.formatting import fmt_cpis, fmt_cps, fmt_significance, fmt_threshold, fmt_winning_probability


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _quantile_summary(series: pd.Series) -> Dict[str, Optional[float]]:
    clean = pd.to_numeric(series, errors='coerce').dropna()
    if clean.empty:
        return {"mean": None, "p5": None, "p50": None, "p95": None}
    return {
        "mean": _safe_float(clean.mean()),
        "p5": _safe_float(clean.quantile(0.05)),
        "p50": _safe_float(clean.quantile(0.50)),
        "p95": _safe_float(clean.quantile(0.95)),
    }


def build_incrementality_summary_context(
    test_name: str,
    significance_threshold: float,
    results_df: pd.DataFrame,
    win_prob_df: pd.DataFrame,
    samples_df: pd.DataFrame,
    ci_df: pd.DataFrame,
) -> Dict[str, Any]:
    metrics: List[Dict[str, Any]] = []

    for metric in win_prob_df['metric'].unique():
        metric_win = win_prob_df[win_prob_df['metric'] == metric]
        metric_samples = samples_df[samples_df['metric'] == metric]
        metric_ci = ci_df[ci_df['conversion_segment'] == metric]
        cells: List[Dict[str, Any]] = []

        for _, row in metric_win.iterrows():
            cell_name = row['cell']
            cell_samples = metric_samples[metric_samples['cell'] == cell_name]
            ci_row = metric_ci[metric_ci['study_name'] == cell_name]
            ci_payload = {}
            if not ci_row.empty:
                ci_record = ci_row.iloc[0]
                point_estimate = _safe_float(ci_record.get('absolute_lift'))
                ci_half_width = _safe_float(ci_record.get('absolutelift_CI'))
                ci_payload = {
                    "incremental_conversions_point_estimate": point_estimate,
                    "ci_half_width": ci_half_width,
                    "ci_excludes_zero": (
                        point_estimate is not None
                        and ci_half_width is not None
                        and (point_estimate - ci_half_width) > 0
                    ),
                }

            cells.append({
                "cell": cell_name,
                "winning_probability": _safe_float(row.get('win_prob')),
                "cpis_usd": _safe_float(row.get('cpis')),
                "absolute_cvr_lift": _safe_float(row.get('cvr_lift')),
                "relative_cvr_lift": _safe_float(row.get('relative_cvr_lift')),
                "incremental_conversions": _safe_float(row.get('incremental_conversions')),
                "significance": _safe_float(row.get('conf_level')),
                "eligible_to_win": bool(row.get('significance_eligible')),
                "confidence_interval": ci_payload,
                "density_summary": {
                    "absolute_cvr_lift": _quantile_summary(cell_samples.get('cvr_lift_samples', pd.Series(dtype=float))),
                    "relative_cvr_lift": _quantile_summary(cell_samples.get('relative_cvr_lift_samples', pd.Series(dtype=float))),
                    "incremental_conversions": _quantile_summary(cell_samples.get('incremental_conversion_samples', pd.Series(dtype=float))),
                },
            })

        winner = max(cells, key=lambda cell: cell.get('winning_probability') or 0.0)
        metrics.append({
            "metric": metric,
            "significance_threshold": significance_threshold,
            "cells": cells,
            "top_winner_by_winning_probability": winner["cell"],
        })

    return {
        "test_type": "incrementality",
        "test_name": test_name,
        "methodology": {
            "winning_probability_rule": (
                "Lowest simulated CPiS among cells that meet the significance threshold "
                "and produce positive incremental conversions"
            ),
            "significance_threshold": significance_threshold,
        },
        "metrics": metrics,
    }


def build_split_summary_context(
    test_name: str,
    compare_on: str,
    win_prob_df: pd.DataFrame,
    samples_df: pd.DataFrame,
) -> Dict[str, Any]:
    metrics: List[Dict[str, Any]] = []

    for metric in win_prob_df['metric'].unique():
        metric_win = win_prob_df[win_prob_df['metric'] == metric]
        metric_samples = samples_df[samples_df['metric'] == metric]
        cells: List[Dict[str, Any]] = []

        for _, row in metric_win.iterrows():
            cell_name = row['cell']
            cell_samples = metric_samples[metric_samples['cell'] == cell_name]
            cells.append({
                "cell": cell_name,
                "winning_probability": _safe_float(row.get('win_prob')),
                "cps_usd": _safe_float(row.get('cps')),
                "users_reached": _safe_float(row.get('users')),
                "conversions": _safe_float(row.get('conversions')),
                "conversion_rate": _safe_float(row.get('conversion_rate')),
                "impressions": _safe_float(row.get('impressions')),
                "lift_vs_zero": _safe_float(row.get('lift_vs_zero')),
                "ci_low": _safe_float(row.get('ci_low')),
                "ci_high": _safe_float(row.get('ci_high')),
                "p_value": _safe_float(row.get('p_value')),
                "density_summary": _quantile_summary(cell_samples.get('metric_samples', pd.Series(dtype=float))),
            })

        winner = max(cells, key=lambda cell: cell.get('winning_probability') or 0.0)
        metrics.append({
            "metric": metric,
            "comparison_metric": compare_on,
            "cells": cells,
            "top_winner_by_winning_probability": winner["cell"],
        })

    return {
        "test_type": "split",
        "test_name": test_name,
        "methodology": {
            "winning_probability_rule": (
                f"Highest simulated {compare_on} using Bayesian posteriors with practical equivalence (ROPE)"
            ),
            "comparison_metric": compare_on,
        },
        "metrics": metrics,
    }


def build_rule_based_summary(context: Dict[str, Any]) -> str:
    lines = [
        "### AI Summary (rule-based fallback)",
        "",
        "_LLM API is not configured. Showing a deterministic summary from computed metrics._",
        "",
    ]

    for metric_block in context.get("metrics", []):
        metric_name = metric_block.get("metric", "Unknown metric")
        winner = metric_block.get("top_winner_by_winning_probability", "N/A")
        lines.append(f"**{metric_name}**")
        lines.append(f"- Recommended winner by Winning Probability: **{winner}**")

        if context.get("test_type") == "incrementality":
            threshold = metric_block.get("significance_threshold")
            ineligible = [
                cell["cell"]
                for cell in metric_block.get("cells", [])
                if not cell.get("eligible_to_win")
            ]
            if threshold is not None:
                lines.append(f"- Significance threshold: **{fmt_threshold(threshold)}**")
            if ineligible:
                lines.append(
                    f"- Ineligible cells due to significance: {', '.join(ineligible)}"
                )

        for cell in sorted(
            metric_block.get("cells", []),
            key=lambda item: item.get("winning_probability") or 0.0,
            reverse=True,
        ):
            win_prob = cell.get("winning_probability")
            win_prob_text = fmt_winning_probability(win_prob) if win_prob is not None else "N/A"
            if context.get("test_type") == "incrementality":
                cpis = cell.get("cpis_usd")
                cpis_text = fmt_cpis(cpis) if cpis is not None else "N/A"
                lines.append(
                    f"- {cell['cell']}: Winning Probability {win_prob_text}, "
                    f"CPiS {cpis_text}, Significance "
                    f"{fmt_significance(cell.get('significance') or 0)}"
                )
            else:
                cps = cell.get("cps_usd")
                cps_text = fmt_cps(cps) if cps is not None else "N/A"
                lines.append(
                    f"- {cell['cell']}: Winning Probability {win_prob_text}, CPS {cps_text}"
                )

        lines.append(
            "- CI plots show uncertainty around each cell's point estimate; wider bars imply less precision."
        )
        lines.append(
            "- Density plots show the distribution of plausible outcomes; right-shifted curves imply stronger performance on that metric."
        )
        lines.append("")

    return "\n".join(lines).strip()


def _build_prompt(context: Dict[str, Any], audience: str = "marketer") -> List[Dict[str, str]]:
    if audience == "analyst":
        tone = "Use precise statistical language, cite uncertainty, and reference posterior overlap and eligibility rules."
    else:
        tone = "Use plain language for marketing stakeholders. Avoid jargon where possible."

    system_prompt = (
        "You are a media test analytics assistant for Disney and Hulu incrementality/split tests. "
        f"{tone} "
        "Use only the provided JSON. Do not invent metrics. "
        "If no cell is eligible or winning probability is split, say so clearly."
    )
    user_prompt = (
        "Summarize this media test analysis.\n\n"
        "Return markdown with EXACTLY these section headers:\n"
        "## Recommended Winner\n"
        "## Why This Cell Won\n"
        "## Efficiency and Impact\n"
        "## Significance and Caveats\n"
        "## Confidence Interval Interpretation\n"
        "## Density Plot Interpretation\n"
        "## Final Recommendation\n\n"
        f"Input JSON:\n{json.dumps(context, indent=2, default=str)}"
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _build_prompt_legacy(context: Dict[str, Any]) -> List[Dict[str, str]]:
    return _build_prompt(context, audience="marketer")


def build_structured_rule_based_summary(context: Dict[str, Any], talking_points: Optional[Dict[str, List[str]]] = None) -> str:
    sections = ["## Recommended Winner", ""]
    for metric_block in context.get("metrics", []):
        metric_name = metric_block.get("metric", "Unknown metric")
        winner = metric_block.get("top_winner_by_winning_probability", "N/A")
        sections.append(f"**{metric_name}:** {winner}")
        if talking_points:
            for cell, bullets in talking_points.items():
                if bullets:
                    sections.append(f"- **{cell}:** {bullets[0]}")
    sections.extend(["", "## Why This Cell Won", build_rule_based_summary(context)])
    return "\n".join(sections)


def _call_azure_openai(messages: List[Dict[str, str]]) -> str:
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    if not api_key or not endpoint:
        raise RuntimeError("Azure OpenAI environment variables are not configured.")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    # SECURITY-REVIEW: external HTTP call with aggregated test metrics; API key from environment only
    response = requests.post(
        url,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "messages": messages,
            "temperature": 0.2,
        },
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"]


def generate_analysis_summary(
    context: Dict[str, Any],
    use_llm: bool = True,
    audience: str = "marketer",
    talking_points: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, str]:
    cache_key = hashlib.sha256(
        json.dumps({"context": context, "audience": audience}, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    if not use_llm:
        return {
            "summary": build_structured_rule_based_summary(context, talking_points),
            "source": "rule_based",
            "cache_key": cache_key,
        }

    try:
        summary = _call_azure_openai(_build_prompt(context, audience=audience))
        return {
            "summary": summary,
            "source": "azure_openai",
            "cache_key": cache_key,
        }
    except Exception:
        return {
            "summary": build_structured_rule_based_summary(context, talking_points),
            "source": "rule_based_fallback",
            "cache_key": cache_key,
        }


def context_cache_key(context: Dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(context, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
