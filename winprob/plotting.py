"""Chart helpers and figure export utilities."""

from io import BytesIO

import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from matplotlib.lines import Line2D

from winprob.config import GREEN, GRID, NAVY, RED, TEXT
from winprob.charts_plotly import _format_ci_point_label


def figure_to_png_bytes(fig) -> bytes:
    """Render a matplotlib figure to PNG bytes and close the figure."""
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def render_ci_errorbar_figure(
    plot_df,
    *,
    title: str,
    y_label: str,
    point_col: str,
    lo_col: str,
    hi_col: str,
    as_percent: bool = False,
):
    """Matplotlib CI error-bar chart for export and offline use."""
    if plot_df.empty:
        return None

    scale = 100.0 if as_percent else 1.0
    fig, ax = plt.subplots(figsize=(10, 5))
    y_max = float("-inf")
    for _, row in plot_df.iterrows():
        cell = row["study_name"]
        point = float(row[point_col]) * scale
        lo = float(row[lo_col]) * scale
        hi = float(row[hi_col]) * scale
        y_max = max(y_max, hi, point)
        ax.errorbar(
            x=[cell],
            y=[point],
            yerr=[[point - lo], [hi - point]],
            fmt="o",
            color=GREEN,
            ecolor=GREEN,
            capsize=5,
            capthick=2,
        )
        ax.annotate(
            _format_ci_point_label(point, as_percent),
            xy=(cell, point),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            va="bottom",
            color=TEXT,
            fontsize=10,
        )
    ax.axhline(0, color=RED, linestyle="--", linewidth=1.5)
    ax.set_title(title)
    ax.set_ylabel(y_label)
    if y_max > float("-inf"):
        ax.set_ylim(top=y_max * 1.12)
    plt.xticks(rotation=25, ha="right")
    ax.legend(
        handles=[
            Line2D(
                [0], [0], marker="o", color="w", markerfacecolor=GREEN,
                markersize=8, label="Point estimate",
            ),
            Line2D([0], [0], color=GREEN, linewidth=3, label="95% CI"),
        ],
        loc="upper right",
    )
    apply_dark_axes(ax, zero_line=False)
    fig.tight_layout()
    return fig


def render_incrementality_density_grid(plot_df, sample_col, x_label, x_tick_format='percent'):
    """Render a faceted KDE density plot for incrementality test samples."""
    sns.set_context('talk')
    sns.set_style('darkgrid')

    grid = sns.FacetGrid(
        plot_df,
        row='metric',
        hue='cell',
        height=3.5,
        aspect=2
    )
    grid.map(sns.kdeplot, sample_col, shade=True)
    grid.set_titles(row_template="{row_name}")
    grid.set_axis_labels(x_label, "Density")

    for ax in grid.axes.flat:
        apply_dark_axes(ax, zero_line=True)
        ax.set_yticklabels(['{:,.0f}'.format(x) for x in ax.get_yticks()])
        if x_tick_format == 'percent':
            ax.set_xticklabels(['{:.2%}'.format(x) for x in ax.get_xticks()])
        else:
            ax.set_xticklabels(['{:,.0f}'.format(x) for x in ax.get_xticks()])

        leg = ax.legend(title="Cells", loc='upper left', bbox_to_anchor=(1.02, 1))
        if leg:
            for text in leg.get_texts():
                text.set_color("white")
            leg.get_title().set_color("white")

    return grid.fig


def apply_dark_axes(ax, zero_line=True):
    """
    Apply the same dark theme
    """
    ax.set_facecolor(NAVY)
    ax.figure.set_facecolor(NAVY)
    
    # Axis labels, title, ticks
    ax.title.set_color(TEXT)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    ax.tick_params(colors=TEXT)
    
    # Grid and spines
    ax.grid(True, color=GRID, alpha=0.3)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    
    # Legend text color
    legend = ax.get_legend()
    if legend:
        plt.setp(legend.get_texts(), color=TEXT)
        plt.setp(legend.get_title(), color=TEXT)
    
    # Optional red zero line
    if zero_line:
        ax.axhline(0, color=RED, linestyle='--', linewidth=1.5)


# session_state figure caching
def cache_and_download_figure(fig, key, filename_prefix):
    if key not in st.session_state:
        buf_png = BytesIO()
        fig.savefig(buf_png, format="png", bbox_inches="tight")
        buf_png.seek(0)

        st.session_state[key] = {
            "png": buf_png.getvalue(),
        }

    st.download_button(
        f"Download {key} PNG",
        data=st.session_state[key]["png"],
        file_name=f"{filename_prefix}.png",
        mime="image/png"
    )


def cache_csv(df, key):
    if key not in st.session_state:
        st.session_state[key] = df.to_csv(index=False).encode("utf-8")