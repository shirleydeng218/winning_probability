"""Interactive Plotly charts."""

from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from winprob.config import GREEN, NAVY, TEXT


def _dark_layout(title: str, height: int = 420) -> Dict:
    return {
        "title": title,
        "paper_bgcolor": NAVY,
        "plot_bgcolor": NAVY,
        "font": {"color": TEXT},
        "height": height,
        "legend": {"orientation": "h", "y": -0.2},
    }


def render_radar_chart(win_prob_df: pd.DataFrame, metric: str) -> None:
    sub = win_prob_df[win_prob_df["metric"] == metric].copy()
    if sub.empty:
        return

    metrics_map = {
        "Winning Probability": "win_prob",
        "CPiS (inverted)": "cpis",
        "Incremental Conversions": "incremental_conversions",
        "Relative CVR Lift": "relative_cvr_lift",
        "Significance": "conf_level",
    }
    normalized_rows = []
    for label, col in metrics_map.items():
        values = sub[col].astype(float)
        if col == "cpis":
            values = 1 / values.replace(0, np.nan)
        min_v, max_v = values.min(), values.max()
        norm = (values - min_v) / (max_v - min_v) if max_v > min_v else values * 0 + 0.5
        for cell, val in zip(sub["cell"], norm):
            normalized_rows.append({"Cell": cell, "Metric": label, "Score": val})

    plot_df = pd.DataFrame(normalized_rows)
    fig = px.line_polar(
        plot_df,
        r="Score",
        theta="Metric",
        color="Cell",
        line_close=True,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(**_dark_layout(f"Cell Comparison — {metric}"))
    fig.update_polars(
        bgcolor=NAVY,
        radialaxis=dict(gridcolor="#2F5175", linecolor="#2F5175", tickfont={"color": TEXT}),
        angularaxis=dict(gridcolor="#2F5175", linecolor="#2F5175", tickfont={"color": TEXT}),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_bump_chart(rank_df: pd.DataFrame, metric: str) -> None:
    rank_cols = [c for c in rank_df.columns if c.startswith("Rank:")]
    if not rank_cols:
        return
    long_rows = []
    for _, row in rank_df.iterrows():
        for col in rank_cols:
            long_rows.append({
                "Cell": row["Cell"],
                "Dimension": col.replace("Rank: ", ""),
                "Rank": row[col],
            })
    plot_df = pd.DataFrame(long_rows)
    fig = px.line(
        plot_df,
        x="Dimension",
        y="Rank",
        color="Cell",
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_yaxes(autorange="reversed", title="Rank (1 = best)")
    fig.update_layout(**_dark_layout(f"Multi-Metric Rankings — {metric}"))
    st.plotly_chart(fig, use_container_width=True)


def render_pairwise_heatmap(pairwise_df: pd.DataFrame, metric: str, winning_rule: str) -> None:
    if pairwise_df.empty:
        return
    z = pairwise_df.astype(float).values
    fig = go.Figure(data=go.Heatmap(
        z=z,
        x=pairwise_df.columns.tolist(),
        y=pairwise_df.index.tolist(),
        colorscale="Viridis",
        zmin=0,
        zmax=1,
        text=np.round(z, 2),
        texttemplate="%{text}",
        hovertemplate="P(row beats col): %{z:.1%}<extra></extra>",
    ))
    fig.update_layout(**_dark_layout(f"Pairwise Win Matrix — {metric}", height=460))
    fig.update_layout(xaxis_title="Column cell", yaxis_title="Row cell")
    st.caption(f"Each cell shows the probability the row cell beats the column cell under **{winning_rule}**.")
    st.plotly_chart(fig, use_container_width=True)


def render_interactive_density(samples_df: pd.DataFrame, metric: str, sample_col: str, title: str, as_percent: bool = False) -> None:
    sub = samples_df[samples_df["metric"] == metric]
    if sub.empty or sample_col not in sub.columns:
        return
    rows = []
    for _, row in sub.iterrows():
        vals = row[sample_col]
        if isinstance(vals, pd.Series):
            vals = vals.explode().values
        elif not isinstance(vals, np.ndarray):
            vals = np.array([vals])
        for v in pd.to_numeric(vals, errors="coerce"):
            if pd.isna(v):
                continue
            display_val = v * 100 if as_percent and sample_col != "incremental_conversion_samples" else v
            rows.append({"Cell": row["cell"], "Value": display_val})
    plot_df = pd.DataFrame(rows)
    if plot_df.empty:
        return
    fig = px.histogram(
        plot_df,
        x="Value",
        color="Cell",
        barmode="overlay",
        opacity=0.55,
        nbins=40,
        histnorm="probability density",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(**_dark_layout(title))
    st.plotly_chart(fig, use_container_width=True)


def _ci_bounds(row: pd.Series, point: float) -> tuple:
    """Derive lower/upper CI from uploaded test readout fields."""
    if "absolute_lift_CI_min" in row.index and "absolute_lift_CI_max" in row.index:
        inc_lo = pd.to_numeric(row.get("absolute_lift_CI_min"), errors="coerce")
        inc_hi = pd.to_numeric(row.get("absolute_lift_CI_max"), errors="coerce")
        if pd.notna(inc_lo) and pd.notna(inc_hi):
            return float(inc_lo), float(inc_hi)

    half = pd.to_numeric(row.get("absolutelift_CI"), errors="coerce")
    if pd.notna(half):
        inc_lo = point - half
        inc_hi = point + half
        return float(inc_lo), float(inc_hi)

    return point, point


def _render_ci_errorbar(
    rows: pd.DataFrame,
    *,
    title: str,
    y_label: str,
    point_col: str,
    lo_col: str,
    hi_col: str,
    as_percent: bool = False,
) -> None:
    if rows.empty:
        return

    scale = 100.0 if as_percent else 1.0
    fig = go.Figure()
    for _, row in rows.iterrows():
        cell = row["study_name"]
        point = float(row[point_col]) * scale
        lo = float(row[lo_col]) * scale
        hi = float(row[hi_col]) * scale
        fig.add_trace(
            go.Scatter(
                x=[cell, cell],
                y=[lo, hi],
                mode="lines",
                line={"color": GREEN, "width": 3},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[cell],
                y=[point],
                mode="markers",
                marker={"color": GREEN, "size": 10},
                name=cell,
            )
        )
    fig.add_hline(y=0, line_dash="dash", line_color="#F87171")
    fig.update_layout(**_dark_layout(title))
    fig.update_yaxes(title=y_label)
    st.plotly_chart(fig, use_container_width=True)


def render_incrementality_ci_plots(ci_df: pd.DataFrame, metric: str) -> None:
    """CI error bars from uploaded test readout for Relative CVR Lift and Incremental Conversions."""
    plot_df = prepare_incrementality_ci_plot_df(ci_df, metric)
    if plot_df.empty:
        return

    st.markdown(f"**{metric} — Relative CVR Lift**")
    _render_ci_errorbar(
        plot_df,
        title=f"Relative CVR Lift CI — {metric}",
        y_label="Relative CVR Lift (%)",
        point_col="relative_point",
        lo_col="relative_lo",
        hi_col="relative_hi",
        as_percent=True,
    )
    st.markdown(f"**{metric} — Incremental Conversions**")
    _render_ci_errorbar(
        plot_df,
        title=f"Incremental Conversions CI — {metric}",
        y_label="Incremental Conversions",
        point_col="incremental_point",
        lo_col="incremental_lo",
        hi_col="incremental_hi",
        as_percent=False,
    )


def prepare_incrementality_ci_plot_df(ci_df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Build CI plot data for Relative CVR Lift and Incremental Conversions."""
    sub = ci_df[ci_df["conversion_segment"] == metric].copy()
    if sub.empty:
        return pd.DataFrame()

    plot_rows = []
    for _, row in sub.iterrows():
        n_test = float(row["treatment_user_count"])
        n_control = float(row["control_user_count"])
        test_rate = float(row["treatment_conversions"]) / n_test if n_test > 0 else 0.0
        control_rate = float(row["control_conversions"]) / n_control if n_control > 0 else 0.0

        incremental = (test_rate - control_rate) * n_test
        if "relative_lift" in row.index and pd.notna(row.get("relative_lift")):
            relative = float(row["relative_lift"])
        elif control_rate > 0:
            relative = (test_rate - control_rate) / control_rate
        else:
            relative = np.nan

        inc_lo, inc_hi = _ci_bounds(row, incremental)
        if control_rate > 0 and n_test > 0:
            rel_lo = (inc_lo / n_test) / control_rate
            rel_hi = (inc_hi / n_test) / control_rate
        else:
            rel_lo = rel_hi = relative

        plot_rows.append({
            "study_name": row["study_name"],
            "relative_point": relative,
            "relative_lo": rel_lo,
            "relative_hi": rel_hi,
            "incremental_point": incremental,
            "incremental_lo": inc_lo,
            "incremental_hi": inc_hi,
        })

    return pd.DataFrame(plot_rows)
