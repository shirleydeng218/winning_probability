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
        "Absolute CVR Lift": "cvr_lift",
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


def render_ci_plotly(ci_df: pd.DataFrame, metric: str) -> None:
    sub = ci_df[ci_df["conversion_segment"] == metric]
    if sub.empty:
        return
    fig = go.Figure()
    for _, row in sub.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["study_name"], row["study_name"]],
            y=[row["absolute_lift"] - row["absolutelift_CI"], row["absolute_lift"] + row["absolutelift_CI"]],
            mode="lines",
            line={"color": GREEN, "width": 3},
            showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[row["study_name"]],
            y=[row["absolute_lift"]],
            mode="markers",
            marker={"color": GREEN, "size": 10},
            name=row["study_name"],
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="#F87171")
    fig.update_layout(**_dark_layout(f"Incremental Conversions CI — {metric}"))
    fig.update_yaxes(title="Incremental Conversions")
    st.plotly_chart(fig, use_container_width=True)
