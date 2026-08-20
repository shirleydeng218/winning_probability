"""Export utilities for readout packs."""

from io import BytesIO
from typing import Any, Dict, Optional

import pandas as pd


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


def build_readout_html(
    test_name: str,
    summary_table: pd.DataFrame,
    ai_summary: Optional[str] = None,
    extra_sections: Optional[Dict[str, str]] = None,
) -> bytes:
    sections = [
        f"<h1>WinProb Readout — {test_name}</h1>",
        "<h2>Winning Probability Summary</h2>",
        summary_table.to_html(index=False),
    ]
    if extra_sections:
        for title, body in extra_sections.items():
            sections.append(f"<h2>{title}</h2><pre>{body}</pre>")
    if ai_summary:
        sections.append(f"<h2>AI Summary</h2><pre>{ai_summary}</pre>")

    html = f"""
    <html><head><meta charset='utf-8'>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 2rem; color: #12263A; }}
      h1 {{ color: #0B1C2D; }}
      table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
      th {{ background: #0B1C2D; color: white; }}
      pre {{ white-space: pre-wrap; background: #f5f7fa; padding: 1rem; border-radius: 8px; }}
    </style></head><body>
    {''.join(sections)}
    </body></html>
    """
    return html.encode("utf-8")


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
