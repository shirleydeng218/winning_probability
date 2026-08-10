# Winning Probability Streamlit App

This Streamlit app computes winning probabilities for multi-cell incrementality tests (Facebook, YouTube, The Trade Desk).

Quick start

1. Create and activate a Python environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
streamlit run app.py
```

Or with Docker:

```bash
docker build -t winprob .
docker run -p 8501:8501 winprob
```

Legacy entry points (`winning_prob_app.py`, `winning_prob_app_llm.py`) still work but `app.py` is the recommended entry point.

Notes

- Upload a CSV or XLSX test file from the supported vendors. The app expects vendor-specific columns; refer to the script for exact mappings.
- Use the `Run Analysis` button and select conversion metrics to compute results.
- Use the download buttons to export density figures (PNG/PDF) and CSV outputs.

Dev

- Consider adding unit tests for the parsing and posterior logic.
- The sampling logic is vectorized for better performance.
\

## Winning Probability Tool

## Overview

The Winning Probability (WP) Tool evaluates A/B(/C/…) experiments by estimating
the probability that each test cell is the best performer, accounting for
uncertainty in observed results.

It is designed to support:
- Multi-cell experiment evaluation
- Close-call decision making
- Complementary use with frequentist statistics

---

## Core Idea

Instead of relying solely on point estimates or pairwise p-values, the tool:
1. Models uncertainty in each cell’s conversion rate
2. Simulates thousands of plausible outcomes
3. Calculates how often each cell wins

The result is a probabilistic ranking of test variants.

---

## Inputs

For each test cell:
- Number of users
- Number of conversions
- Spend / cost metrics
- Metric identifier (e.g. Purchase)

Data is aggregated at the (date, metric, cell) level before analysis.

---

## Methodology

### Conversion Rate Modeling
- Each cell’s CVR is modeled using a Beta posterior
- Weak prior: Beta(1, 1)
- Posterior parameters:
  - α = 1 + conversions
  - β = 1 + users − conversions

This naturally reflects sample size and uncertainty.

---

### Monte Carlo Simulation
- Draw N samples from each cell’s posterior CVR distribution
- In each simulation, compare all cells simultaneously
- Identify the winning cell per simulation

---

### Winning Probability
Winning Probability is defined as:
> The fraction of simulations in which a cell performs best.

---

## Outputs

For each cell:
- Winning Probability
- Posterior CVR distribution
- Frequentist confidence intervals
- Pairwise p-values vs baseline (optional)

---

## Interpretation Guidelines

- WP ≈ 0.5 → cells are effectively tied
- Higher WP → more likely to be the best option
- WP complements, but does not replace, statistical significance

---

## Design Principles

- Conservative uncertainty modeling
- Multi-cell safe comparisons
- Transparent, simulation-based logic
- Decision-oriented outputs

---

## What This Tool Is / Is Not

**IS**
- A ranking and decision-support tool
- Robust to overlapping confidence intervals
- Suitable for A/B/C+ tests

**IS NOT**
- A p-value
- A guarantee of future performance
- A replacement for business judgment

---

## Recommended Usage

Use Winning Probability to:
- Rank variants
- Resolve close tests
- Inform rollout decisions

Use frequentist stats to:
- Communicate uncertainty
- Validate directional signals
- Align with experimentation standards
