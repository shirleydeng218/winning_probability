"""Analytics helpers for split-test readouts."""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from winprob.formatting import (
    LABEL_CPS,
    LABEL_WINNING_PROBABILITY,
    fmt_count,
    fmt_cps,
    fmt_cvr_lift,
    fmt_winning_probability,
)


def _rank_cells(sub: pd.DataFrame) -> pd.DataFrame:
    ranked = sub.copy()
    ranked["_cps_score"] = -ranked["cps"].replace(0, np.nan)
    return ranked.sort_values(["win_prob", "_cps_score"], ascending=[False, False]).reset_index(drop=True)


def summarize_split_leader(win_prob_df: pd.DataFrame, metric: str) -> Dict:
    sub = win_prob_df[win_prob_df["metric"] == metric]
    if sub.empty:
        return {}

    ranked = _rank_cells(sub)
    winner = ranked.iloc[0]
    runner_up = ranked.iloc[1] if len(ranked) > 1 else None
    best_cps = sub.loc[sub["cps"].idxmin()] if sub["cps"].notna().any() else None
    return {
        "winner_cell": winner["cell"],
        "win_prob": float(winner["win_prob"]),
        "cps": float(winner["cps"]),
        "conversion_rate": float(winner["conversion_rate"]),
        "conversions": float(winner["conversions"]),
        "users": float(winner["users"]),
        "runner_up_cell": runner_up["cell"] if runner_up is not None else None,
        "runner_up_win_prob": float(runner_up["win_prob"]) if runner_up is not None else None,
        "best_cps_cell": best_cps["cell"] if best_cps is not None else None,
        "best_cps_value": float(best_cps["cps"]) if best_cps is not None else None,
    }


def build_split_bottom_line(win_prob_df: pd.DataFrame, metric: str, compare_on_label: str) -> str:
    leader = summarize_split_leader(win_prob_df, metric)
    if not leader:
        return ""
    return (
        f"Recommend **{leader['winner_cell']}** for {metric}: "
        f"{fmt_winning_probability(leader['win_prob'])} Winning Probability, "
        f"{fmt_cps(leader['cps'])} CPS, "
        f"{fmt_cvr_lift(leader['conversion_rate'])} CVR "
        f"(ranked on **{compare_on_label}** with ROPE-aware tie-breaking)."
    )


def build_split_stakeholder_table(win_prob_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return pd.DataFrame()

    ranked = _rank_cells(sub)
    leader = summarize_split_leader(win_prob_df, metric)
    winner_cell = leader.get("winner_cell")
    runner_up_cell = leader.get("runner_up_cell")
    points = generate_split_talking_points(win_prob_df, metric)

    rows = []
    for _, row in ranked.iterrows():
        cell = row["cell"]
        status = "Recommended" if cell == winner_cell else ("Runner-up" if cell == runner_up_cell else "Alternative")
        rows.append({
            "Cell": cell,
            "Status": status,
            LABEL_WINNING_PROBABILITY: row["win_prob"],
            LABEL_CPS: row["cps"],
            "Takeaway": points.get(cell, [""])[0],
        })
    return pd.DataFrame(rows)


def generate_split_talking_points(win_prob_df: pd.DataFrame, metric: str) -> Dict[str, List[str]]:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return {}

    leader = summarize_split_leader(win_prob_df, metric)
    winner_cell = leader.get("winner_cell")
    runner_up_cell = leader.get("runner_up_cell")
    points: Dict[str, List[str]] = {}

    for _, row in sub.iterrows():
        cell = row["cell"]
        win_prob = float(row["win_prob"])
        cps = float(row["cps"])
        cvr = float(row["conversion_rate"])
        conv = float(row["conversions"])

        if cell == winner_cell:
            takeaway = (
                f"Recommended — {fmt_winning_probability(win_prob)} Winning Probability, "
                f"{fmt_cps(cps)} CPS, {fmt_cvr_lift(cvr)} CVR."
            )
        elif cell == runner_up_cell:
            takeaway = f"Runner-up — {fmt_winning_probability(win_prob)} Winning Probability, {fmt_cps(cps)} CPS."
        elif np.isfinite(cps) and cps == sub["cps"].min():
            takeaway = f"Most efficient — {fmt_cps(cps)} CPS; {fmt_winning_probability(win_prob)} Winning Probability."
        elif conv == sub["conversions"].max():
            takeaway = f"Highest volume — {fmt_count(conv)} conversions at {fmt_cps(cps)} CPS."
        else:
            takeaway = (
                f"{fmt_winning_probability(win_prob)} Winning Probability, "
                f"{fmt_cps(cps)} CPS, {fmt_cvr_lift(cvr)} CVR."
            )
        points[cell] = [takeaway]
    return points


def build_split_multi_metric_rankings(win_prob_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return pd.DataFrame()

    ranking_specs = [
        ("win_prob", LABEL_WINNING_PROBABILITY, False),
        ("cps", LABEL_CPS, True),
        ("conversion_rate", "Conversion Rate", False),
        ("conversions", "Conversions", False),
        ("users", "Reach", False),
    ]
    rows = []
    for _, row in sub.iterrows():
        entry = {"Cell": row["cell"]}
        for col, label, _asc in ranking_specs:
            if col in row.index:
                entry[label] = row[col]
        rows.append(entry)

    rank_df = pd.DataFrame(rows)
    for col, label, ascending in ranking_specs:
        if label not in rank_df.columns:
            continue
        rank_df[f"Rank: {label}"] = rank_df[label].rank(ascending=ascending, method="min").astype(int)
    return rank_df
