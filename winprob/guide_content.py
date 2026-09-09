"""Contextual copy for the Bayes on-page guide."""

from __future__ import annotations

from typing import Dict, List

SECTION_TIPS: Dict[str, str] = {
    "home": "Pick incrementality if you have a control, or split test for A/B/C cells.",
    "upload_validate": "Upload your test file or try sample data to see how WinProb works.",
    "input_validation": "Green checks mean your file is ready to analyze.",
    "configure_analysis": "Set how a winner is picked and which conversion metrics to include.",
    "test_overview": "Quick sanity check on cells, spend, and metrics before results load.",
    "executive_summary": "Start here — who's winning and how confident the read is (Confident vs Directional).",
    "per_cell_metrics": "Raw performance by cell — spend, lift, CPiS, and significance.",
    "multi_metric_rankings": "See how cells rank across winning probability, CPiS, lift, and significance.",
    "cell_comparison": "A normalized snapshot of how cells compare on key dimensions.",
    "distribution_uncertainty": "Winning probability comes from many simulations — explore the spread here.",
    "advanced_analysis": "Optional deep dives — open only what you need for your story.",
    "winning_probability_summary": "Full scoreboard across every metric and cell in one table.",
    "ai_summary": "Turn results into a narrative you can paste or export.",
    "export_readout_pack": "Download a branded pack for stakeholders — include your AI summary first.",
    "default": "Scroll through sections — I'll explain what you're looking at.",
}

EXPANDER_TIPS: Dict[str, str] = {
    "Confidence intervals": "Uncertainty bands from your uploaded test — not from simulation.",
    "Interactive density plots": "Hover to see how often each outcome showed up in simulation.",
    "Static density plots (export-ready)": "Download-ready charts for decks and stakeholder readouts.",
    "Pairwise Win Matrix": "Head-to-head — how often one cell beats another.",
    "Posterior Overlap": "Shows when two cells look statistically similar.",
    "Budget Optimizer": "What if you shifted more budget to each cell?",
}

SECTION_ID_RULES: List[Dict[str, str]] = [
    {"id": "upload-validate", "key": "upload_validate"},
    {"id": "input-validation", "key": "input_validation"},
    {"id": "configure-analysis", "key": "configure_analysis"},
    {"id": "test-overview", "key": "test_overview"},
    {"id": "winning-probability-summary", "key": "winning_probability_summary"},
    {"id": "ai-summary", "key": "ai_summary"},
    {"id": "export-readout-pack", "key": "export_readout_pack"},
    {"suffix": "-executive-summary", "key": "executive_summary"},
    {"suffix": "-per-cell-metrics", "key": "per_cell_metrics"},
    {"suffix": "-multi-metric-rankings", "key": "multi_metric_rankings"},
    {"suffix": "-cell-comparison", "key": "cell_comparison"},
    {"suffix": "-distribution-uncertainty", "key": "distribution_uncertainty"},
    {"suffix": "-advanced-analysis", "key": "advanced_analysis"},
]


def resolve_section_key(section_id: str) -> str:
    for rule in SECTION_ID_RULES:
        if rule.get("id") == section_id:
            return rule["key"]
        suffix = rule.get("suffix")
        if suffix and section_id.endswith(suffix):
            return rule["key"]
    return "default"


def build_guide_payload() -> Dict[str, object]:
    """Serialize tips for the client-side guide component."""
    return {
        "sections": SECTION_TIPS,
        "expanders": EXPANDER_TIPS,
        "rules": SECTION_ID_RULES,
        "home": SECTION_TIPS["home"],
        "default": SECTION_TIPS["default"],
    }
