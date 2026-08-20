"""App introduction and methodology copy."""

import streamlit as st

from winprob.ui_styles import render_hero, render_quick_start

APP_DOCS_URL = (
    "https://docs.google.com/document/d/1XgL30F5GybUdpCsJemZ0kCmOeFwRZDxizqZFM9dJpu8/edit?tab=t.0"
)
SLIDES_URL = (
    "https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit"
)


def render_app_intro() -> None:
    render_hero(
        "Estimate **Winning Probability** across test cells, compare "
        "**CPiS**, **Relative CVR lift**, and **Incremental Conversions**, "
        "and generate a stakeholder-ready executive summary. Use the sidebar to explore scenarios "
        "without re-uploading data."
    )
    render_quick_start()

    with st.expander("About WinProb & methodology", expanded=False):
        st.markdown(
            f"""
This application evaluates media test performance for Disney+ and Hulu. It supports
**incrementality tests** (with a control group) and **split tests** (A/B/C without a control).

For incrementality tests, Winning Probability is based on the lowest simulated **CPiS** among
cells that meet a minimum **significance threshold** and produce positive incremental conversions.

**Why this helps when results are uncertain**

Media tests rarely deliver a perfectly clear winner. Sample sizes, noisy conversion rates, and
overlapping confidence intervals mean a single point estimate (e.g., one CPiS or lift number)
can be misleading. WinProb **quantifies statistical uncertainty** by asking: *given what we
observed, how often would each cell win if we repeated this test under similar conditions?*

Instead of a binary "significant or not" read, you get:
- **Winning Probability** — how likely each cell is the best choice under your winning rule
- **Confidence intervals & density plots** — how wide the plausible range of lift and efficiency is
- **Pairwise comparisons & overlap** — whether cells are truly separated or effectively tied

This supports better decisions when stakeholders need to choose a cell to scale, defend a
recommendation, or acknowledge a close call rather than over-interpreting a noisy leader.

**Core approach**
1. **Model uncertainty** — Bayesian Beta posterior for each cell's conversion rate.
2. **Simulate outcomes** — Monte Carlo draws for CVR, lift, CPiS, and incremental conversions.
3. **Compare cells** — Rank cells each simulation under your winning rule.
4. **Winning Probability** — Share of simulations where a cell wins among eligible cells.

**Interpretation**
- Winning Probability near 50% → close call; consider overlap, CPiS, and business constraints.
- Higher Winning Probability → stronger case to scale, especially when Significance is met.
- Low Winning Probability with good CPiS → efficient but not consistently best across simulations.
- Always combine with significance, confidence intervals, and business context—not a standalone decision.

**Resources:** [App documentation]({APP_DOCS_URL}) · [Slides]({SLIDES_URL})

**Support:** Shirley Deng or Max Wilson (BLADE) —
[shirley.deng@disney.com](mailto:shirley.deng@disney.com) ·
[maxim.wilson@disney.com](mailto:maxim.wilson@disney.com)
            """
        )

    st.markdown("---")
