"""Bayesian simulation engine for split (A/B/C) tests."""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

COMPARE_ON_OPTIONS = {
    "conversion_rate": "Conversion rate (CVR)",
    "conversions": "Total conversions",
    "reach": "Reach (users)",
    "impressions": "Impressions",
}


def build_split_results(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """Build per-cell rows for simulation from standardized upload data."""
    rows = []
    for objective in metrics_df["conversion_segment"].unique():
        obj_df = metrics_df[metrics_df["conversion_segment"] == objective]
        for dt in obj_df["analysis_date"].unique():
            dt_df = obj_df[obj_df["analysis_date"] == dt]
            for _, r in dt_df.iterrows():
                conversions = int(r.get("treatment_conversions", 0) or 0)
                users = int(r.get("treatment_user_count", 0) or 0)
                users = users if users > 0 else 1
                rows.append({
                    "dt": dt,
                    "cell": r.get("study_name", "Unknown"),
                    "metric": objective,
                    "conversions": conversions,
                    "population_test": users,
                    "conversion_rate": conversions / users,
                    "impressions": float(r.get("impressions", 0) or 0),
                    "spend": float(r.get("experiment_cost_usd", 0) or 0),
                    "cps": float(r.get("cps", 0) or 0),
                })
    return pd.DataFrame(rows)


def _score_samples(
    theta_samples: np.ndarray,
    population: np.ndarray,
    impressions: np.ndarray,
    compare_on: str,
) -> np.ndarray:
    if compare_on == "conversion_rate":
        return theta_samples
    if compare_on == "conversions":
        return theta_samples * population[:, None]
    if compare_on == "reach":
        return population[:, None]
    if compare_on == "impressions":
        return impressions[:, None]
    raise ValueError(f"Unsupported compare_on: {compare_on}")


def _add_frequentist_stats(win_prob_df: pd.DataFrame, compare_on: str) -> pd.DataFrame:
    out = []
    for (dt, metric), sub in win_prob_df.groupby(["dt", "metric"]):
        sub = sub.reset_index(drop=True)
        for _, r in sub.iterrows():
            n = r["users"]
            x = r["conversions"]
            ci_low = ci_high = p_value = np.nan
            lift = r.get("lift_vs_zero", r.get("conversion_rate", 0))

            if compare_on == "conversion_rate" and n > 0:
                p = r["conversion_rate"]
                se = np.sqrt(p * (1 - p) / n)
                z = norm.ppf(0.975)
                ci_low = p - z * se
                ci_high = p + z * se
                p_value = 1 - norm.cdf(p / se) if se > 0 else np.nan
            elif compare_on == "conversions":
                se = np.sqrt(max(x, 0))
                ci_low = max(0, x - 1.96 * se)
                ci_high = x + 1.96 * se
                p_value = 1 - norm.cdf(x / se) if se > 0 else np.nan
            elif compare_on == "reach":
                ci_low = ci_high = r["users"]
            elif compare_on == "impressions":
                ci_low = ci_high = r["impressions"]

            out.append({
                "dt": dt,
                "cell": r["cell"],
                "metric": metric,
                "lift_vs_zero": lift,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "p_value": p_value,
            })
    return pd.DataFrame(out)


def run_split_simulation(
    results: pd.DataFrame,
    *,
    n_sims: int,
    compare_on: str = "conversion_rate",
    seed: int = 1234,
    rope_eps: float = 1e-4,
    alpha_prior: float = 1.0,
    beta_prior: float = 1.0,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, pd.DataFrame], Dict[str, pd.DataFrame]]:
    """Return win probabilities, posterior samples, pairwise matrices, and overlap tables."""
    rng = np.random.default_rng(seed)
    win_prob_rows = []
    samples_rows = []
    pairwise_by_metric: Dict[str, pd.DataFrame] = {}
    overlap_by_metric: Dict[str, pd.DataFrame] = {}

    for (dt, metric), sub in results.groupby(["dt", "metric"]):
        sub = sub.reset_index(drop=True)
        n_cells = sub.shape[0]
        if n_cells == 0:
            continue

        theta_samples = np.vstack([
            rng.beta(
                alpha_prior + sub.loc[i, "conversions"],
                beta_prior + sub.loc[i, "population_test"] - sub.loc[i, "conversions"],
                size=n_sims,
            )
            for i in range(n_cells)
        ])
        population = sub["population_test"].values
        impressions = sub["impressions"].values
        score_samples = _score_samples(theta_samples, population, impressions, compare_on)

        winners = np.zeros(n_cells, dtype=int)
        for s in range(n_sims):
            best = np.max(score_samples[:, s])
            close = np.where(best - score_samples[:, s] <= rope_eps)[0]
            winners[rng.choice(close)] += 1

        win_probs = winners / n_sims
        cells = sub["cell"].tolist()
        sim_store = []

        for i in range(n_cells):
            conv_rate = sub.loc[i, "conversions"] / sub.loc[i, "population_test"]
            win_prob_rows.append({
                "dt": dt,
                "cell": sub.loc[i, "cell"],
                "metric": metric,
                "win_prob": win_probs[i],
                "users": sub.loc[i, "population_test"],
                "conversions": sub.loc[i, "conversions"],
                "conversion_rate": conv_rate,
                "impressions": sub.loc[i, "impressions"],
                "spend": sub.loc[i, "spend"],
                "cps": sub.loc[i, "cps"],
                "lift_vs_zero": conv_rate if compare_on == "conversion_rate" else score_samples[i].mean(),
            })
            sim_store.append(score_samples[i])
            samples_rows.append({
                "analysis_date": dt,
                "cell": sub.loc[i, "cell"],
                "metric": metric,
                "metric_samples": score_samples[i],
                "cvr_samples": theta_samples[i],
                "population_test": sub.loc[i, "population_test"],
                "conversions": sub.loc[i, "conversions"],
                "impressions": sub.loc[i, "impressions"],
            })

        pairwise = pd.DataFrame(index=cells, columns=cells, dtype=float)
        for a, cell_a in enumerate(cells):
            for b, cell_b in enumerate(cells):
                if a == b:
                    pairwise.loc[cell_a, cell_b] = np.nan
                else:
                    pairwise.loc[cell_a, cell_b] = (sim_store[a] > sim_store[b]).mean()

        overlap_rows = []
        for a, cell_a in enumerate(cells):
            for b, cell_b in enumerate(cells):
                if a >= b:
                    continue
                overlap_rows.append({
                    "cell_a": cell_a,
                    "cell_b": cell_b,
                    "p_a_beats_b": (sim_store[a] > sim_store[b]).mean(),
                    "p_b_beats_a": (sim_store[b] > sim_store[a]).mean(),
                    "p_similar_cvr": (np.abs(theta_samples[a] - theta_samples[b]) <= rope_eps).mean(),
                })

        pairwise_by_metric[metric] = pairwise
        overlap_by_metric[metric] = pd.DataFrame(overlap_rows)

    win_prob_df = pd.DataFrame(win_prob_rows)
    samples_df = pd.DataFrame(samples_rows)
    if win_prob_df.empty:
        return win_prob_df, samples_df, pairwise_by_metric, overlap_by_metric

    freq_df = _add_frequentist_stats(win_prob_df, compare_on)
    win_prob_df = win_prob_df.merge(freq_df, on=["dt", "cell", "metric"], how="left")
    return win_prob_df, samples_df, pairwise_by_metric, overlap_by_metric
