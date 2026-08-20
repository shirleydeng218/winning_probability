"""Export utilities for readout packs."""

import base64
import html
from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd

from winprob.charts_plotly import prepare_incrementality_ci_plot_df
from winprob.plotting import figure_to_png_bytes, render_ci_errorbar_figure, render_incrementality_density_grid

ReadoutChart = Dict[str, Any]


def _pdf_safe(text: str) -> str:
    """Normalize text for core PDF fonts (Helvetica supports Latin-1 only)."""
    replacements = {
        "\u2014": "-",  # em dash
        "\u2013": "-",  # en dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _pdf_reset_cursor(pdf) -> None:
    """Return cursor to the left margin after images or wide content."""
    pdf.set_x(pdf.l_margin)


def _pdf_write_block(pdf, text: str, *, line_height: int = 6, font_size: int = 10, style: str = "") -> None:
    _pdf_reset_cursor(pdf)
    pdf.set_font("Helvetica", style=style, size=font_size)
    pdf.multi_cell(pdf.epw, line_height, _pdf_safe(text))


def _pdf_write_table(pdf, summary_table: pd.DataFrame, *, font_size: int = 8, line_height: int = 5) -> None:
    """Render a dataframe as wrapped PDF lines instead of one unbreakable row."""
    display = summary_table.copy()
    for col in display.select_dtypes(include="object"):
        display[col] = display[col].astype(str).map(lambda v: _pdf_safe(v)[:80])

    headers = [_pdf_safe(str(col)) for col in display.columns]
    _pdf_write_block(pdf, " | ".join(headers), font_size=font_size, line_height=line_height, style="B")
    _pdf_reset_cursor(pdf)
    pdf.ln(1)

    for _, row in display.iterrows():
        cells = [_pdf_safe(str(row[col]))[:80] for col in display.columns]
        _pdf_write_block(pdf, " | ".join(cells), font_size=font_size, line_height=line_height)
        _pdf_reset_cursor(pdf)
        pdf.ln(0.5)


def build_readout_charts(df: pd.DataFrame, samples_df: pd.DataFrame) -> List[ReadoutChart]:
    """Build CI and static density PNG charts for readout export."""
    charts: List[ReadoutChart] = []

    for metric in sorted(df["conversion_segment"].unique()):
        plot_df = prepare_incrementality_ci_plot_df(df, metric)
        if plot_df.empty:
            continue

        rel_fig = render_ci_errorbar_figure(
            plot_df,
            title=f"Relative CVR Lift CI — {metric}",
            y_label="Relative CVR Lift (%)",
            point_col="relative_point",
            lo_col="relative_lo",
            hi_col="relative_hi",
            as_percent=True,
        )
        if rel_fig is not None:
            charts.append({
                "title": f"{metric} — Relative CVR Lift CI",
                "png_bytes": figure_to_png_bytes(rel_fig),
            })

        inc_fig = render_ci_errorbar_figure(
            plot_df,
            title=f"Incremental Conversions CI — {metric}",
            y_label="Incremental Conversions",
            point_col="incremental_point",
            lo_col="incremental_lo",
            hi_col="incremental_hi",
            as_percent=False,
        )
        if inc_fig is not None:
            charts.append({
                "title": f"{metric} — Incremental Conversions CI",
                "png_bytes": figure_to_png_bytes(inc_fig),
            })

    if samples_df.empty:
        return charts

    density_plot_df = samples_df[[
        "analysis_date", "cell", "metric",
        "relative_cvr_lift_samples", "incremental_conversion_samples",
    ]].copy()

    for title, col, fmt in [
        ("Relative CVR Lift", "relative_cvr_lift_samples", "percent"),
        ("Incremental Conversions", "incremental_conversion_samples", "count"),
    ]:
        sub = density_plot_df.dropna(subset=[col])
        if sub.empty:
            continue
        fig = render_incrementality_density_grid(
            sub[["analysis_date", "cell", "metric", col]],
            col,
            title,
            x_tick_format=fmt,
        )
        charts.append({
            "title": f"Density — {title}",
            "png_bytes": figure_to_png_bytes(fig),
        })

    return charts


def build_readout_html(
    test_name: str,
    summary_table: pd.DataFrame,
    ai_summary: Optional[str] = None,
    extra_sections: Optional[Dict[str, str]] = None,
    charts: Optional[List[ReadoutChart]] = None,
) -> bytes:
    safe_name = html.escape(test_name)
    sections = [
        f"<h1>WinProb Readout — {safe_name}</h1>",
        "<h2>Winning Probability Summary</h2>",
        summary_table.to_html(index=False, escape=True),
    ]
    if extra_sections:
        for title, body in extra_sections.items():
            sections.append(
                f"<h2>{html.escape(title)}</h2><pre>{html.escape(body)}</pre>"
            )
    if charts:
        sections.append("<h2>Confidence Intervals &amp; Density Plots</h2>")
        for chart in charts:
            title = html.escape(str(chart["title"]))
            encoded = base64.b64encode(chart["png_bytes"]).decode("ascii")
            sections.append(
                f'<h3>{title}</h3>'
                f'<img alt="{title}" src="data:image/png;base64,{encoded}" '
                f'style="max-width:100%;margin-bottom:1.5rem;" />'
            )
    if ai_summary:
        sections.append(f"<h2>AI Summary</h2><pre>{html.escape(ai_summary)}</pre>")

    html_doc = f"""
    <html><head><meta charset='utf-8'>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; color: #12263A; }}
      h1 {{ color: #0B1C2D; }}
      h3 {{ color: #0B1C2D; margin-top: 1.25rem; }}
      table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
      th {{ background: #0B1C2D; color: white; }}
      pre {{ white-space: pre-wrap; background: #f5f7fa; padding: 1rem; border-radius: 8px; }}
      img {{ border: 1px solid #d9e2ec; border-radius: 8px; }}
    </style></head><body>
    {''.join(sections)}
    </body></html>
    """
    return html_doc.encode("utf-8")


def build_readout_pdf_bytes(
    test_name: str,
    summary_table: pd.DataFrame,
    extra_sections: Optional[Dict[str, str]] = None,
    charts: Optional[List[ReadoutChart]] = None,
) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _pdf_write_block(pdf, f"WinProb Readout — {test_name}", line_height=10, font_size=16, style="B")
    pdf.ln(4)

    if extra_sections:
        for title, body in extra_sections.items():
            _pdf_write_block(pdf, title, line_height=8, font_size=12, style="B")
            _pdf_write_block(pdf, body, line_height=6, font_size=11)
            pdf.ln(2)

    _pdf_write_block(pdf, "Winning Probability Summary", line_height=8, font_size=12, style="B")
    pdf.ln(2)
    _pdf_write_table(pdf, summary_table)

    if charts:
        pdf.ln(4)
        _pdf_write_block(pdf, "Confidence Intervals & Density Plots", line_height=8, font_size=12, style="B")
        for chart in charts:
            pdf.ln(3)
            _pdf_write_block(pdf, str(chart["title"]), line_height=7, font_size=11, style="B")
            pdf.ln(1)
            try:
                _pdf_reset_cursor(pdf)
                pdf.image(BytesIO(chart["png_bytes"]), w=pdf.epw)
                _pdf_reset_cursor(pdf)
                pdf.ln(2)
            except Exception:
                _pdf_write_block(pdf, "[Chart could not be embedded]", line_height=6, font_size=10)

    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


def build_simple_pdf_bytes(title: str, lines: list[str]) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, _pdf_safe(title))
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        pdf.multi_cell(0, 7, _pdf_safe(line))
        pdf.ln(1)
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()
