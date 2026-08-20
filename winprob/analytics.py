"""Derived analytics: rankings, budget optimizer."""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from winprob.formatting import (
    LABEL_CPIS,
    LABEL_WINNING_PROBABILITY,
    fmt_count,
    fmt_cpis,
    fmt_relative_cvr_lift,
    fmt_significance,
    fmt_threshold,
    fmt_winning_probability,
)


def _rule_sort_score(row: pd.Series, winning_rule: str) -> float:
    """Higher score = better under the selected winning rule."""
    if winning_rule == "lowest_cpis":
        cpis = float(row["cpis"])
        return -cpis if np.isfinite(cpis) else -np.inf
    if winning_rule == "highest_incremental":
        return float(row["incremental_conversions"])
    if winning_rule == "highest_cvr_lift":
        return float(row["relative_cvr_lift"])
    raise ValueError(f"Unknown winning rule: {winning_rule}")


def _rank_cells(
    sub: pd.DataFrame,
    winning_rule: str = "lowest_cpis",
) -> pd.DataFrame:
    """Rank cells by Winning Probability, tie-breaking with the winning rule."""
    ranked = sub.copy()
    ranked["_rule_score"] = ranked.apply(lambda row: _rule_sort_score(row, winning_rule), axis=1)
    return ranked.sort_values(
        ["win_prob", "_rule_score"],
        ascending=[False, False],
    ).reset_index(drop=True)


def _leader_and_runner_up(
    sub: pd.DataFrame,
    winning_rule: str = "lowest_cpis",
) -> Tuple[Optional[pd.Series], Optional[pd.Series]]:
    if sub.empty:
        return None, None
    ranked = _rank_cells(sub, winning_rule)
    winner = ranked.iloc[0]
    runner_up = ranked.iloc[1] if len(ranked) > 1 else None
    return winner, runner_up


def build_multi_metric_rankings(win_prob_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return pd.DataFrame()

    ranking_specs = [
        ("win_prob", "Winning Probability", False),
        ("cpis", "CPiS", True),
        ("incremental_conversions", "Incremental Conversions", False),
        ("relative_cvr_lift", "Relative CVR Lift", False),
        ("conf_level", "Significance", False),
    ]

    rows = []
    for _, row in sub.iterrows():
        entry = {"Cell": row["cell"]}
        for col, label, ascending in ranking_specs:
            if col not in row.index:
                continue
            entry[label] = row[col]
        rows.append(entry)

    rank_df = pd.DataFrame(rows)
    for col, label, ascending in ranking_specs:
        if label not in rank_df.columns:
            continue
        rank_df[f"Rank: {label}"] = rank_df[label].rank(ascending=ascending, method="min").astype(int)
    return rank_df


def compute_budget_optimizer(
    win_prob_df: pd.DataFrame,
    metric: str,
    additional_budget: float,
) -> pd.DataFrame:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty or additional_budget <= 0:
        return pd.DataFrame()

    rows = []
    for _, row in sub.iterrows():
        cpis = row["cpis"]
        inc = row["incremental_conversions"]
        spend = row["spend"]
        if cpis and cpis > 0 and np.isfinite(cpis):
            projected_incremental = additional_budget / cpis
            projected_total_incremental = inc + projected_incremental
        else:
            projected_incremental = np.nan
            projected_total_incremental = np.nan
        rows.append({
            "Cell": row["cell"],
            "Current Spend": spend,
            "Current CPiS": cpis,
            "Current Incremental Conversions": inc,
            "Projected Incremental from Added Budget": projected_incremental,
            "Projected Total Incremental Conversions": projected_total_incremental,
            "Eligible": row.get("significance_eligible", False),
        })
    result = pd.DataFrame(rows)
    if "Projected Total Incremental Conversions" in result.columns:
        result = result.sort_values("Projected Total Incremental Conversions", ascending=False)
    return result


def summarize_metric_leader(
    win_prob_df: pd.DataFrame,
    metric: str,
    winning_rule: str = "lowest_cpis",
) -> Dict:
    sub = win_prob_df[win_prob_df["metric"] == metric]
    if sub.empty:
        return {}

    winner, runner_up = _leader_and_runner_up(sub, winning_rule)
    best_cpis = sub.loc[sub["cpis"].idxmin()] if sub["cpis"].notna().any() else None
    return {
        "winner_cell": winner["cell"],
        "win_prob": float(winner["win_prob"]),
        "cpis": float(winner["cpis"]),
        "incremental_conversions": float(winner["incremental_conversions"]),
        "cvr_lift": float(winner["cvr_lift"]),
        "significance": float(winner["conf_level"]),
        "eligible": bool(winner.get("significance_eligible", False)),
        "runner_up_cell": runner_up["cell"] if runner_up is not None else None,
        "runner_up_win_prob": float(runner_up["win_prob"]) if runner_up is not None else None,
        "best_cpis_cell": best_cpis["cell"] if best_cpis is not None else None,
        "best_cpis_value": float(best_cpis["cpis"]) if best_cpis is not None else None,
    }


def _cell_status(
    cell: str,
    winner_cell: str,
    runner_up_cell: Optional[str],
    eligible: bool,
) -> str:
    if cell == winner_cell and eligible:
        return "Recommended"
    if cell == winner_cell and not eligible:
        return "Leads (not eligible)"
    if runner_up_cell and cell == runner_up_cell:
        return "Runner-up"
    if not eligible:
        return "Not eligible"
    return "Alternative"


def build_metric_bottom_line(
    win_prob_df: pd.DataFrame,
    metric: str,
    significance_threshold: float,
    winning_rule: str = "lowest_cpis",
) -> str:
    leader = summarize_metric_leader(win_prob_df, metric, winning_rule)
    if not leader:
        return ""

    cell = leader["winner_cell"]
    if leader["eligible"]:
        return (
            f"Recommend **{cell}** for {metric}: "
            f"{fmt_winning_probability(leader['win_prob'])} Winning Probability, "
            f"{fmt_cpis(leader['cpis'])} CPiS, "
            f"{fmt_count(leader['incremental_conversions'])} Incremental Conversions "
            f"({fmt_significance(leader['significance'])} Significance)."
        )

    runner = leader.get("runner_up_cell")
    runner_note = f" **{runner}** is the next-best eligible option." if runner else ""
    return (
        f"**{cell}** leads on Winning Probability ({fmt_winning_probability(leader['win_prob'])}) "
        f"but is below {fmt_threshold(significance_threshold)} Significance threshold "
        f"({fmt_significance(leader['significance'])}).{runner_note}"
    )


def generate_talking_points(
    win_prob_df: pd.DataFrame,
    metric: str,
    significance_threshold: float = 0.90,
    winning_rule: str = "lowest_cpis",
) -> Dict[str, List[str]]:
    """One concise takeaway per cell for stakeholder readouts."""
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return {}

    ranked = _rank_cells(sub, winning_rule)
    leader = summarize_metric_leader(win_prob_df, metric, winning_rule)
    winner_cell = leader.get("winner_cell")
    runner_up_cell = leader.get("runner_up_cell")
    points: Dict[str, List[str]] = {}

    for _, row in ranked.iterrows():
        cell = row["cell"]
        win_prob = float(row["win_prob"])
        cpis = float(row["cpis"])
        inc = float(row["incremental_conversions"])
        lift = float(row["relative_cvr_lift"])
        conf = float(row["conf_level"])
        eligible = bool(row.get("significance_eligible", False))

        if cell == winner_cell and eligible:
            takeaway = (
                f"Recommended — {fmt_winning_probability(win_prob)} Winning Probability, "
                f"{fmt_cpis(cpis)} CPiS, {fmt_count(inc)} Incremental Conversions."
            )
        elif cell == winner_cell and not eligible:
            takeaway = (
                f"Leads Winning Probability ({fmt_winning_probability(win_prob)}) but below "
                f"{fmt_threshold(significance_threshold)} Significance ({fmt_significance(conf)})."
            )
        elif cell == runner_up_cell:
            takeaway = f"Runner-up — {fmt_winning_probability(win_prob)} Winning Probability, {fmt_cpis(cpis)} CPiS."
        elif np.isfinite(cpis) and cpis == sub["cpis"].min():
            takeaway = f"Most efficient — {fmt_cpis(cpis)} CPiS; {fmt_winning_probability(win_prob)} Winning Probability."
        elif inc == sub["incremental_conversions"].max():
            takeaway = f"Highest volume — {fmt_count(inc)} Incremental Conversions at {fmt_cpis(cpis)} CPiS."
        else:
            takeaway = (
                f"{fmt_winning_probability(win_prob)} Winning Probability, "
                f"{fmt_cpis(cpis)} CPiS, {fmt_relative_cvr_lift(lift)} Relative CVR Lift."
            )

        bullets = [takeaway]
        if not eligible and cell != winner_cell:
            bullets.append(f"Below {fmt_threshold(significance_threshold)} Significance ({fmt_significance(conf)}).")

        points[cell] = bullets[:2]

    return points


def build_stakeholder_summary_table(
    win_prob_df: pd.DataFrame,
    metric: str,
    significance_threshold: float = 0.90,
    winning_rule: str = "lowest_cpis",
) -> pd.DataFrame:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return pd.DataFrame()

    ranked = _rank_cells(sub, winning_rule)
    leader = summarize_metric_leader(win_prob_df, metric, winning_rule)
    winner_cell = leader.get("winner_cell")
    runner_up_cell = leader.get("runner_up_cell")
    points = generate_talking_points(
        win_prob_df, metric, significance_threshold, winning_rule=winning_rule
    )

    rows = []
    for _, row in ranked.iterrows():
        cell = row["cell"]
        rows.append({
            "Cell": cell,
            "Status": _cell_status(
                cell,
                winner_cell,
                runner_up_cell,
                bool(row.get("significance_eligible", False)),
            ),
            LABEL_WINNING_PROBABILITY: row["win_prob"],
            LABEL_CPIS: row["cpis"],
            "Takeaway": points.get(cell, [""])[0],
        })
    return pd.DataFrame(rows)
