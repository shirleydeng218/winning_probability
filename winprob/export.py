"""Export utilities for readout packs."""

import base64
import html
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import pandas as pd

from winprob.charts_plotly import prepare_incrementality_ci_plot_df
from winprob.plotting import figure_to_png_bytes, render_ci_errorbar_figure, render_incrementality_density_grid

ReadoutChart = Dict[str, Any]

# Brand palette (matches winprob/ui_styles.py)
NAVY = "#0B1C2D"
PANEL = "#12263A"
BORDER = "#2F5175"
MINT = "#B8F2E6"
GREEN = "#7ED957"
TEXT = "#E6F2F0"
MUTED = "#9FB3C8"
SURFACE = "#0F2236"


def _pdf_safe(text: str) -> str:
    """Normalize text for core PDF fonts (Helvetica supports Latin-1 only)."""
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
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


def _inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(r"_(.+?)_", r"<em>\1</em>", escaped)
    return escaped


def _markdown_to_html(text: str) -> str:
    """Lightweight markdown renderer for AI summary blocks in HTML exports."""
    parts: List[str] = []
    in_list = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped in {"---", "***"}:
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append('<hr class="winprob-divider" />')
            continue

        if stripped.startswith("## "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f'<h3 class="winprob-md-h2">{_inline_markdown(stripped[3:])}</h3>')
            continue

        if stripped.startswith("### "):
            if in_list:
                parts.append("</ul>")
                in_list = False
            parts.append(f'<h4 class="winprob-md-h3">{_inline_markdown(stripped[4:])}</h4>')
            continue

        if stripped.startswith("- "):
            if not in_list:
                parts.append('<ul class="winprob-md-list">')
                in_list = True
            parts.append(f"<li>{_inline_markdown(stripped[2:])}</li>")
            continue

        if not stripped:
            if in_list:
                parts.append("</ul>")
                in_list = False
            continue

        if in_list:
            parts.append("</ul>")
            in_list = False
        parts.append(f'<p class="winprob-md-p">{_inline_markdown(stripped)}</p>')

    if in_list:
        parts.append("</ul>")
    return "\n".join(parts)


def _readout_css() -> str:
    return f"""
    :root {{
      --navy: {NAVY};
      --panel: {PANEL};
      --border: {BORDER};
      --mint: {MINT};
      --green: {GREEN};
      --text: {TEXT};
      --muted: {MUTED};
      --surface: {SURFACE};
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      padding: 2rem 1.5rem 3rem;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: linear-gradient(180deg, {NAVY} 0%, #081420 100%);
      color: var(--text);
      line-height: 1.55;
    }}

    .winprob-page {{
      max-width: 1100px;
      margin: 0 auto;
    }}

    .winprob-banner {{
      background: linear-gradient(135deg, {NAVY} 0%, {PANEL} 55%, #0f2840 100%);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.35rem 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.22);
    }}

    .winprob-banner-eyebrow {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.72rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--green);
      margin-bottom: 0.4rem;
    }}

    .winprob-banner-title {{
      font-size: clamp(1.5rem, 3vw, 2.1rem);
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1.15;
      background: linear-gradient(90deg, {MINT} 0%, {GREEN} 45%, {MINT} 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin: 0;
    }}

    .winprob-banner-meta {{
      margin-top: 0.55rem;
      color: var(--muted);
      font-size: 0.92rem;
    }}

    .winprob-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      margin-top: 0.9rem;
    }}

    .winprob-pill {{
      display: inline-block;
      background: {PANEL};
      border: 1px solid var(--border);
      color: var(--mint);
      border-radius: 999px;
      padding: 0.28rem 0.75rem;
      font-size: 0.82rem;
      letter-spacing: 0.02em;
    }}

    .winprob-section {{
      margin-bottom: 1.75rem;
    }}

    .winprob-section-header {{
      margin-bottom: 0.85rem;
    }}

    .winprob-section-title {{
      color: var(--mint);
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.01em;
      margin: 0 0 0.3rem 0;
    }}

    .winprob-section-caption {{
      color: var(--muted);
      font-size: 0.9rem;
      margin: 0;
      line-height: 1.45;
    }}

    .winprob-card {{
      background: {PANEL};
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.1rem 1.2rem;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.12);
    }}

    .winprob-table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: {SURFACE};
    }}

    table.winprob-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.86rem;
    }}

    table.winprob-table thead th {{
      background: {PANEL};
      color: var(--mint);
      text-align: left;
      padding: 0.7rem 0.8rem;
      border-bottom: 1px solid var(--border);
      font-size: 0.78rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    table.winprob-table tbody td {{
      padding: 0.62rem 0.8rem;
      border-bottom: 1px solid rgba(47, 81, 117, 0.55);
      color: var(--text);
      vertical-align: top;
    }}

    table.winprob-table tbody tr:nth-child(even) td {{
      background: rgba(18, 38, 58, 0.45);
    }}

    table.winprob-table tbody tr:last-child td {{
      border-bottom: none;
    }}

    .winprob-chart-card {{
      background: {SURFACE};
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.9rem 1rem 1rem;
      margin-bottom: 1rem;
    }}

    .winprob-chart-title {{
      color: var(--text);
      font-size: 0.95rem;
      font-weight: 600;
      margin: 0 0 0.75rem 0;
    }}

    .winprob-chart-card img {{
      display: block;
      width: 100%;
      border-radius: 8px;
      border: 1px solid rgba(47, 81, 117, 0.65);
    }}

    .winprob-summary-body {{
      color: var(--text);
      font-size: 0.94rem;
      line-height: 1.6;
    }}

    .winprob-md-h2 {{
      color: var(--mint);
      font-size: 1.02rem;
      margin: 1rem 0 0.45rem 0;
    }}

    .winprob-md-h3 {{
      color: var(--text);
      font-size: 0.96rem;
      margin: 0.85rem 0 0.35rem 0;
    }}

    .winprob-md-p {{
      margin: 0.35rem 0;
      color: var(--text);
    }}

    .winprob-md-list {{
      margin: 0.35rem 0 0.65rem 1.1rem;
      padding: 0;
      color: var(--text);
    }}

    .winprob-md-list li {{
      margin: 0.25rem 0;
    }}

    .winprob-divider {{
      border: none;
      border-top: 1px solid var(--border);
      margin: 1rem 0;
    }}

    .winprob-footer {{
      margin-top: 2rem;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
      color: var(--muted);
      font-size: 0.8rem;
      text-align: center;
    }}

    @media print {{
      body {{
        background: white;
        color: #12263A;
        padding: 0.5in;
      }}
      .winprob-banner,
      .winprob-card,
      .winprob-chart-card,
      .winprob-table-wrap {{
        box-shadow: none;
        break-inside: avoid;
      }}
      .winprob-banner-title {{
        -webkit-text-fill-color: {NAVY};
        color: {NAVY};
      }}
      table.winprob-table thead th {{
        background: {NAVY};
        color: white;
      }}
      table.winprob-table tbody td {{
        color: #12263A;
      }}
    }}
    """


def _render_banner_html(test_name: str, extra_sections: Optional[Dict[str, str]]) -> str:
    safe_name = html.escape(test_name)
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    pills = ""
    if extra_sections:
        pill_items = "".join(
            f'<span class="winprob-pill">{html.escape(title)}: {html.escape(body)}</span>'
            for title, body in extra_sections.items()
        )
        pills = f'<div class="winprob-pills">{pill_items}</div>'

    return f"""
    <header class="winprob-banner">
      <div class="winprob-banner-eyebrow">BLADE · Bayesian Test Intelligence</div>
      <h1 class="winprob-banner-title">{safe_name}</h1>
      <div class="winprob-banner-meta">WinProb test readout · Generated {html.escape(generated)}</div>
      {pills}
    </header>
    """


def _render_section_html(title: str, caption: str, body_html: str) -> str:
    return f"""
    <section class="winprob-section">
      <div class="winprob-section-header">
        <h2 class="winprob-section-title">{html.escape(title)}</h2>
        <p class="winprob-section-caption">{html.escape(caption)}</p>
      </div>
      {body_html}
    </section>
    """


def _render_table_html(summary_table: pd.DataFrame) -> str:
    table_html = summary_table.to_html(
        index=False,
        escape=True,
        border=0,
        classes="winprob-table",
    )
    return f'<div class="winprob-table-wrap">{table_html}</div>'


def _render_charts_html(charts: List[ReadoutChart]) -> str:
    cards = []
    for chart in charts:
        title = html.escape(str(chart["title"]))
        encoded = base64.b64encode(chart["png_bytes"]).decode("ascii")
        cards.append(
            f'<article class="winprob-chart-card">'
            f'<h3 class="winprob-chart-title">{title}</h3>'
            f'<img alt="{title}" src="data:image/png;base64,{encoded}" />'
            f"</article>"
        )
    return "\n".join(cards)


def _pdf_reset_cursor(pdf) -> None:
    pdf.set_x(pdf.l_margin)


def _pdf_set_header_style(pdf) -> None:
    pdf.set_fill_color(11, 28, 45)
    pdf.set_text_color(184, 242, 230)
    pdf.set_draw_color(47, 81, 117)


def _pdf_set_body_style(pdf) -> None:
    pdf.set_fill_color(255, 255, 255)
    pdf.set_text_color(18, 38, 58)
    pdf.set_draw_color(47, 81, 117)


def _pdf_write_block(pdf, text: str, *, line_height: int = 6, font_size: int = 10, style: str = "") -> None:
    _pdf_reset_cursor(pdf)
    pdf.set_font("Helvetica", style=style, size=font_size)
    pdf.multi_cell(pdf.epw, line_height, _pdf_safe(text))


def _pdf_write_section_title(pdf, title: str) -> None:
    pdf.ln(3)
    _pdf_set_body_style(pdf)
    _pdf_write_block(pdf, title, line_height=8, font_size=13, style="B")
    pdf.ln(1)


def _pdf_write_styled_table(pdf, summary_table: pd.DataFrame) -> None:
    display = summary_table.copy()
    for col in display.select_dtypes(include="object"):
        display[col] = display[col].astype(str).map(lambda v: _pdf_safe(v))

    columns = list(display.columns)
    if not columns:
        return

    col_count = len(columns)
    col_width = pdf.epw / col_count
    row_height = 6
    font_size = 6 if col_count > 7 else 7

    _pdf_set_header_style(pdf)
    pdf.set_font("Helvetica", "B", font_size)
    for col in columns:
        pdf.cell(col_width, row_height + 1, _pdf_safe(str(col))[:28], border=1, align="C", fill=True)
    pdf.ln()

    _pdf_set_body_style(pdf)
    pdf.set_font("Helvetica", size=font_size)
    fill = False
    for _, row in display.iterrows():
        x_start = pdf.l_margin
        y_start = pdf.get_y()
        max_height = row_height

        cell_lines = []
        for col in columns:
            text = _pdf_safe(str(row[col]))
            lines = pdf.multi_cell(col_width, row_height, text, split_only=True)
            cell_lines.append(lines)
            max_height = max(max_height, row_height * max(1, len(lines)))

        if y_start + max_height > pdf.page_break_trigger:
            pdf.add_page()
            y_start = pdf.get_y()

        pdf.set_xy(x_start, y_start)
        for col_index, col in enumerate(columns):
            x = x_start + col_index * col_width
            pdf.set_xy(x, y_start)
            if fill:
                pdf.set_fill_color(245, 248, 252)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.multi_cell(
                col_width,
                row_height,
                _pdf_safe(str(row[col])),
                border=1,
                fill=True,
            )
        fill = not fill
        pdf.set_xy(x_start, y_start + max_height)


def _pdf_render_banner(pdf, test_name: str, extra_sections: Optional[Dict[str, str]]) -> None:
    _pdf_set_header_style(pdf)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(pdf.epw, 7, _pdf_safe("BLADE - Bayesian Test Intelligence"), border=0, fill=True, align="L")
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(pdf.epw, 9, _pdf_safe(test_name), border=0, fill=True, align="L")
    pdf.ln(7)
    pdf.set_font("Helvetica", size=9)
    generated = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    pdf.cell(pdf.epw, 6, _pdf_safe(f"WinProb test readout - Generated {generated}"), border=0, fill=True, align="L")
    pdf.ln(6)

    if extra_sections:
        pill_text = " | ".join(f"{title}: {body}" for title, body in extra_sections.items())
        pdf.set_font("Helvetica", size=8)
        pdf.multi_cell(pdf.epw, 5, _pdf_safe(pill_text), border=0, fill=True)
    pdf.ln(4)
    _pdf_set_body_style(pdf)


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
    sections = [_render_banner_html(test_name, extra_sections)]

    sections.append(
        _render_section_html(
            "Winning Probability Summary",
            "Full results across all conversion metrics and cells.",
            _render_table_html(summary_table),
        )
    )

    if charts:
        sections.append(
            _render_section_html(
                "Confidence Intervals & Density Plots",
                "Input-based uncertainty bands and Monte Carlo posterior distributions.",
                _render_charts_html(charts),
            )
        )

    if ai_summary:
        summary_html = f'<div class="winprob-card winprob-summary-body">{_markdown_to_html(ai_summary)}</div>'
        sections.append(
            _render_section_html(
                "AI Summary",
                "Applied narrative summary from your LLM workflow.",
                summary_html,
            )
        )

    body = "\n".join(sections)
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WinProb Readout — {html.escape(test_name)}</title>
  <style>{_readout_css()}</style>
</head>
<body>
  <main class="winprob-page">
    {body}
    <footer class="winprob-footer">Generated by WinProb · Bayesian media test intelligence</footer>
  </main>
</body>
</html>"""
    return html_doc.encode("utf-8")


def build_readout_pdf_bytes(
    test_name: str,
    summary_table: pd.DataFrame,
    ai_summary: Optional[str] = None,
    extra_sections: Optional[Dict[str, str]] = None,
    charts: Optional[List[ReadoutChart]] = None,
) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        return b""

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.set_margins(12, 12, 12)
    pdf.add_page()
    _pdf_render_banner(pdf, test_name, extra_sections)

    _pdf_write_section_title(pdf, "Winning Probability Summary")
    _pdf_write_styled_table(pdf, summary_table)

    if charts:
        _pdf_write_section_title(pdf, "Confidence Intervals & Density Plots")
        for chart in charts:
            pdf.ln(2)
            _pdf_write_block(pdf, str(chart["title"]), line_height=6, font_size=10, style="B")
            pdf.ln(1)
            try:
                _pdf_reset_cursor(pdf)
                pdf.image(BytesIO(chart["png_bytes"]), w=min(pdf.epw, 180))
                _pdf_reset_cursor(pdf)
                pdf.ln(2)
            except Exception:
                _pdf_write_block(pdf, "[Chart could not be embedded]", line_height=6, font_size=9)

    if ai_summary:
        _pdf_write_section_title(pdf, "AI Summary")
        for line in ai_summary.splitlines():
            stripped = line.strip()
            if not stripped:
                pdf.ln(1)
                continue
            if stripped.startswith("## "):
                _pdf_write_block(pdf, stripped[3:], line_height=6, font_size=11, style="B")
            elif stripped.startswith("### "):
                _pdf_write_block(pdf, stripped[4:], line_height=5, font_size=10, style="B")
            elif stripped.startswith("- "):
                _pdf_write_block(pdf, f"  • {stripped[2:]}", line_height=5, font_size=9)
            elif stripped in {"---", "***"}:
                pdf.ln(1)
            else:
                _pdf_write_block(pdf, stripped, line_height=5, font_size=9)

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
