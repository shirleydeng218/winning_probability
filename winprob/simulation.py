"""Bayesian simulation engine for incrementality tests."""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import beta

WINNING_RULES = {
    "lowest_cpis": "Lowest CPiS (efficiency)",
    "highest_incremental": "Highest incremental conversions (scale)",
    "highest_cvr_lift": "Highest absolute CVR lift (rate)",
}

DEFAULT_SIGNIFICANCE_THRESHOLD = 0.90


def build_posterior_results(metrics_df: pd.DataFrame, alpha_prior: float = 1.0, beta_prior: float = 1.0) -> pd.DataFrame:
    rows = []
    idx = 0
    for objective in metrics_df["conversion_segment"].unique():
        for cell in metrics_df[metrics_df["conversion_segment"] == objective]["study_name"].unique():
            sub = metrics_df[
                (metrics_df["conversion_segment"] == objective) & (metrics_df["study_name"] == cell)
            ].reset_index()
            for dt in metrics_df["analysis_date"].unique():
                row = sub[sub["analysis_date"] == dt].reset_index()
                if row.empty:
                    continue
                r = row.iloc[0]
                test_alpha = alpha_prior + r["treatment_conversions"]
                test_beta = beta_prior + r["treatment_user_count"] - r["treatment_conversions"]
                ctl_alpha = alpha_prior + r["control_conversions"]
                ctl_beta = beta_prior + r["control_user_count"] - r["control_conversions"]
                test_rate = test_alpha / (test_alpha + test_beta)
                ctl_rate = ctl_alpha / (ctl_alpha + ctl_beta)
                cvr_lift = test_rate - ctl_rate
                pdiff = cvr_lift * r["treatment_user_count"]
                if "relative_lift" in row.columns and pd.notnull(r.get("relative_lift")):
                    relative_cvr_lift = r["relative_lift"]
                elif ctl_rate > 0:
                    relative_cvr_lift = cvr_lift / ctl_rate
                else:
                    relative_cvr_lift = np.nan

                rows.append({
                    "dt": dt,
                    "cell": cell,
                    "metric": objective,
                    "test_alpha_posterior": test_alpha,
                    "test_beta_posterior": test_beta,
                    "ctl_alpha_posterior": ctl_alpha,
                    "ctl_beta_posterior": ctl_beta,
                    "cpis": r["cpis"],
                    "spend": r["experiment_cost_usd"],
                    "population_test": r["treatment_user_count"],
                    "conf_level": r["absolute_lift_confidence_level"],
                    "cvr_lift": cvr_lift,
                    "relative_cvr_lift": relative_cvr_lift,
                    "incremental_conversions": pdiff,
                })
                idx += 1
    return pd.DataFrame(rows)


def _score_samples(
    incrementals: np.ndarray,
    cpis_samples: np.ndarray,
    cvr_lift_samples: np.ndarray,
    winning_rule: str,
    eligible: bool,
) -> np.ndarray:
    if not eligible:
        return np.full(len(incrementals), np.inf if winning_rule == "lowest_cpis" else -np.inf)

    if winning_rule == "lowest_cpis":
        return np.where(incrementals > 0, cpis_samples, np.inf)
    if winning_rule == "highest_incremental":
        return np.where(incrementals > 0, incrementals, -np.inf)
    if winning_rule == "highest_cvr_lift":
        return np.where(cvr_lift_samples > 0, cvr_lift_samples, -np.inf)
    raise ValueError(f"Unknown winning rule: {winning_rule}")


def _pick_winner(scores: np.ndarray, winning_rule: str) -> int:
    finite = np.isfinite(scores)
    if not finite.any():
        return -1
    eligible_idx = np.where(finite)[0]
    if winning_rule == "lowest_cpis":
        return int(eligible_idx[np.argmin(scores[eligible_idx])])
    return int(eligible_idx[np.argmax(scores[eligible_idx])])


def run_incrementality_simulation(
    results: pd.DataFrame,
    n_sims: int,
    significance_threshold: float,
    winning_rule: str = "lowest_cpis",
    seed: int = 1234,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    np.random.seed(seed)
    win_prob_df = pd.DataFrame()
    samples_df = pd.DataFrame()
    pairwise_by_metric: Dict[str, pd.DataFrame] = {}
    overlap_by_metric: Dict[str, pd.DataFrame] = {}

    for dt in results["dt"].unique():
        for metric in results["metric"].unique():
            sub_results = results[(results["dt"] == dt) & (results["metric"] == metric)].reset_index(drop=True)
            n_cells = len(sub_results)
            if n_cells == 0:
                continue

            cells = sub_results["cell"].tolist()
            wins = np.zeros(n_cells)
            sim_store: Dict[str, List[np.ndarray]] = {
                "incremental": [],
                "cpis": [],
                "cvr_lift": [],
            }

            score_matrix = []
            for i in range(n_cells):
                conf_level = sub_results.loc[i, "conf_level"]
                spend = sub_results.loc[i, "spend"]
                pop = sub_results.loc[i, "population_test"]
                eligible = conf_level >= significance_threshold and conf_level > 0

                if conf_level > 0:
                    test = beta(sub_results.loc[i, "test_alpha_posterior"], sub_results.loc[i, "test_beta_posterior"]).rvs(n_sims)
                    ctl = beta(sub_results.loc[i, "ctl_alpha_posterior"], sub_results.loc[i, "ctl_beta_posterior"]).rvs(n_sims)
                else:
                    test = np.zeros(n_sims)
                    ctl = np.zeros(n_sims)

                cvr_lift_samples = test - ctl
                incrementals = cvr_lift_samples * pop
                with np.errstate(divide="ignore", invalid="ignore"):
                    cpis_samples = spend / incrementals

                sim_store["incremental"].append(incrementals)
                sim_store["cpis"].append(cpis_samples)
                sim_store["cvr_lift"].append(cvr_lift_samples)
                score_matrix.append(
                    _score_samples(incrementals, cpis_samples, cvr_lift_samples, winning_rule, eligible)
                )

                sub_row = pd.DataFrame({
                    "analysis_date": dt,
                    "cell": sub_results.loc[i, "cell"],
                    "metric": metric,
                    "spend": spend,
                    "population_test": pop,
                    "test_samples": test,
                    "control_samples": ctl,
                })
                samples_df = pd.concat([samples_df, sub_row], ignore_index=True)

            score_matrix = np.vstack(score_matrix)
            for s in range(n_sims):
                col = score_matrix[:, s]
                winner = _pick_winner(col, winning_rule)
                if winner >= 0:
                    wins[winner] += 1

            sub_results = sub_results.copy()
            sub_results["win_prob"] = wins / n_sims
            sub_results["significance_eligible"] = sub_results["conf_level"] >= significance_threshold
            win_prob_df = pd.concat([win_prob_df, sub_results], ignore_index=True)

            pairwise = pd.DataFrame(index=cells, columns=cells, dtype=float)
            for a, cell_a in enumerate(cells):
                for b, cell_b in enumerate(cells):
                    if a == b:
                        pairwise.loc[cell_a, cell_b] = np.nan
                    else:
                        if winning_rule == "lowest_cpis":
                            pairwise.loc[cell_a, cell_b] = (sim_store["cpis"][a] < sim_store["cpis"][b]).mean()
                        elif winning_rule == "highest_incremental":
                            pairwise.loc[cell_a, cell_b] = (sim_store["incremental"][a] > sim_store["incremental"][b]).mean()
                        else:
                            pairwise.loc[cell_a, cell_b] = (sim_store["cvr_lift"][a] > sim_store["cvr_lift"][b]).mean()

            overlap_rows = []
            for a, cell_a in enumerate(cells):
                for b, cell_b in enumerate(cells):
                    if a >= b:
                        continue
                    overlap_rows.append({
                        "cell_a": cell_a,
                        "cell_b": cell_b,
                        "p_a_beats_b_incremental": (sim_store["incremental"][a] > sim_store["incremental"][b]).mean(),
                        "p_a_beats_b_cpis": (sim_store["cpis"][a] < sim_store["cpis"][b]).mean(),
                        "p_a_beats_b_cvr": (sim_store["cvr_lift"][a] > sim_store["cvr_lift"][b]).mean(),
                    })
            pairwise_by_metric[metric] = pairwise
            overlap_by_metric[metric] = pd.DataFrame(overlap_rows)

    if not samples_df.empty:
        samples_df["cvr_lift_samples"] = samples_df["test_samples"] - samples_df["control_samples"]
        with np.errstate(divide="ignore", invalid="ignore"):
            samples_df["relative_cvr_lift_samples"] = np.where(
                samples_df["control_samples"] > 0,
                samples_df["cvr_lift_samples"] / samples_df["control_samples"],
                np.nan,
            )
        samples_df["incremental_conversion_samples"] = (
            samples_df["cvr_lift_samples"] * samples_df["population_test"]
        )
        samples_df["cpis_samples"] = samples_df["spend"] / samples_df["incremental_conversion_samples"]

    return win_prob_df, samples_df, pairwise_by_metric, overlap_by_metric


def run_sensitivity_analysis(
    results: pd.DataFrame,
    n_sims: int,
    winning_rule: str,
    thresholds: Optional[List[float]] = None,
) -> pd.DataFrame:
    if thresholds is None:
        thresholds = [0.50, 0.60, 0.70, 0.80, 0.90, 0.95]

    rows = []
    for threshold in thresholds:
        win_prob_df, _, _, _ = run_incrementality_simulation(
            results, n_sims=n_sims, significance_threshold=threshold, winning_rule=winning_rule
        )
        for metric in win_prob_df["metric"].unique():
            sub = win_prob_df[win_prob_df["metric"] == metric]
            if sub.empty:
                continue
            winner_row = sub.loc[sub["win_prob"].idxmax()]
            eligible_count = sub["significance_eligible"].sum()
            rows.append({
                "metric": metric,
                "significance_threshold": threshold,
                "winner": winner_row["cell"],
                "winning_probability": winner_row["win_prob"],
                "eligible_cells": int(eligible_count),
            })
    return pd.DataFrame(rows)
