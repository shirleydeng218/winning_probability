# Import packages
import matplotlib
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from scipy.stats import beta, norm
import seaborn as sns
from io import BytesIO
from datetime import datetime


# Set Title
st.title('Winning Probability App for Evaluating D+ & Hulu Media Tests')

# ------------------------
# Functions
# ------------------------
def cache_figure(fig, key_prefix):
    """
    Save figure bytes to session_state so downloads don't force recompute.
    """
    png_key = f"{key_prefix}_png"
    pdf_key = f"{key_prefix}_pdf"

    if png_key not in st.session_state or pdf_key not in st.session_state:
        try:
            buf_png = BytesIO()
            fig.savefig(buf_png, format="png", bbox_inches="tight")
            buf_png.seek(0)
            st.session_state[png_key] = buf_png.getvalue()

            buf_pdf = BytesIO()
            fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
            buf_pdf.seek(0)
            st.session_state[pdf_key] = buf_pdf.getvalue()
        except Exception:
            pass


def compute_win_probabilities(
    results,
    n_sims,
    compare_on='conversion_rate',
    seed=1234,
    rope_eps=1e-4,          # ~1 basis point CVR
    alpha_prior=5.0,
    beta_prior=5.0
):
    """
    Bayesian winning probability with practical equivalence (ROPE).
    Avoids degenerate 0/100 outcomes in large-sample tests.
    """

    rng = np.random.default_rng(seed)
    win_prob_rows = []
    samples_rows = []

    for (dt, metric), sub in results.groupby(['dt', 'metric']):
        sub = sub.reset_index(drop=True)
        n_cells = sub.shape[0]

        if n_cells == 0:
            continue

        # ---- Sample posteriors ----
        theta_samples = np.vstack([
            rng.beta(alpha_prior + sub.loc[i, 'conversions'],
                     beta_prior + sub.loc[i, 'population_test'] - sub.loc[i, 'conversions'],
                     size=n_sims)
            for i in range(n_cells)
        ])

        # ---- Select comparison metric ----
        if compare_on == 'conversion_rate':
            score_samples = theta_samples
        elif compare_on == 'conversions':
            score_samples = theta_samples * sub['population_test'].values[:, None]
        elif compare_on == 'reach':
            score_samples = sub['population_test'].values[:, None]  # absolute reach
        elif compare_on == 'impressions':
            score_samples = sub['impressions'].values[:, None]
        else:
            raise ValueError(f"Unsupported compare_on: {compare_on}")

        # ---- ROPE-aware winner assignment ----
        winners = np.zeros(n_cells, dtype=int)
        for s in range(n_sims):
            best = np.max(score_samples[:, s])
            close = np.where(best - score_samples[:, s] <= rope_eps)[0]
            winner = rng.choice(close)
            winners[winner] += 1

        win_probs = winners / n_sims

        # ---- Store results ----
        for i in range(n_cells):
            win_prob_rows.append({
                'dt': dt,
                'cell': sub.loc[i, 'cell'],
                'metric': metric,
                'win_prob': win_probs[i],
                'users': sub.loc[i, 'population_test'],
                'conversions': sub.loc[i, 'conversions'],
                'conversion_rate': sub.loc[i, 'conversions'] / sub.loc[i, 'population_test'],
                'impressions': sub.loc[i, 'impressions'],
                'cps': sub.loc[i, 'cps'],
            })

            samples_rows.append(pd.DataFrame({
                'date': dt,
                'cell': sub.loc[i, 'cell'],
                'metric': metric,
                'metric_samples': score_samples[i],
                'population_test': sub.loc[i, 'population_test'],
                'conversions': sub.loc[i, 'conversions'],
                'impressions': sub.loc[i, 'impressions'],
            }))

    win_prob_df = pd.DataFrame(win_prob_rows)
    samples_df = pd.concat(samples_rows, ignore_index=True)
    return win_prob_df, samples_df


def add_frequentist_stats(win_prob_df, compare_on='conversion_rate'):
    """
    Add confidence intervals for each cell vs 0 (absolute metric).
    """
    out = []

    for (dt, metric), sub in win_prob_df.groupby(['dt', 'metric']):
        sub = sub.reset_index(drop=True)
        for i, r in sub.iterrows():
            n = r['users']
            x = r['conversions']
            ci_low = ci_high = p_value = np.nan
            lift = r[compare_on] if compare_on in r else 0

            if compare_on == 'conversion_rate' and n > 0:
                p = r['conversion_rate']
                se = np.sqrt(p * (1 - p) / n)
                z = norm.ppf(0.975)
                ci_low = p - z * se
                ci_high = p + z * se
                p_value = 1 - norm.cdf(p / se)
            elif compare_on == 'conversions':
                # Normal approximation for counts
                se = np.sqrt(x)
                ci_low = max(0, x - 1.96 * se)
                ci_high = x + 1.96 * se
                p_value = 1 - norm.cdf(x / se) if se > 0 else np.nan
            elif compare_on == 'reach':
                ci_low = ci_high = r['users']
                p_value = np.nan
            elif compare_on == 'impressions':
                ci_low = ci_high = r['impressions']
                p_value = np.nan

            out.append({
                'dt': dt,
                'cell': r['cell'],
                'metric': metric,
                'lift_vs_zero': lift,
                'ci_low': ci_low,
                'ci_high': ci_high,
                'p_value': p_value
            })

    return pd.DataFrame(out)


# ------------------------
# Streamlit App
# ------------------------
"""
This app calculates the winning probability of cells in split tests we run with our media vendors.
This methodology is based on Hulu's proprietary winning probability framework.
See [here](https://docs.google.com/document/d/1XgL30F5GybUdpCsJemZ0kCmOeFwRZDxizqZFM9dJpu8/edit?tab=t.0) for App Documentation, or reach out to Max Wilson or Shirley Deng on the BLADE team at maxim.wilson@disney.com or shirley.deng@disney.com for more information.
"""


st.subheader('Test Parameters')
"""
See [here](https://docs.google.com/spreadsheets/d/1XCZSbQNNYVPRl7AEICgsLKCGi-Re_Owk/edit?gid=1708648830#gid=1708648830) for an input template with the correct format.
"""

input_file = st.file_uploader('Upload Test Data as a CSV or Excel file:', type=['csv', 'xlsx'])
if input_file is None:
    st.stop()
elif input_file.name.endswith('.xlsx'):
    raw = pd.read_excel(input_file)
elif input_file.name.endswith('.csv'):
    raw = pd.read_csv(input_file)
else:
    st.write('Please upload a csv or xlsx file.')
    st.stop()

n_sims = st.slider('Select the number of simulations to run:', 1000, 100000, 5000)

df = raw.copy()

# Standardize column names
df['treatment_cvr'] = df['test_conv_rate']
df['conversion_segment'] = df['event_type']
df['treatment_user_count'] = df['n_test']
df['treatment_conversions'] = df['test_conversions']
df['study_name'] = df['cell_name']
df['experiment_cost_usd'] = df['spend_usd']
df['impressions'] = df['impressions']
df['cps'] = df['CPS']

df['analysis_date'] = datetime.now().strftime('%Y-%m-%d')

conversion_metrics = st.multiselect('Select conversion metric(s) to analyze:',
                                    sorted(df['conversion_segment'].unique()))

if not conversion_metrics:
    st.write('Please select at least one conversion metric.')
    st.stop()

# Filter to selected metrics
df = df[df['conversion_segment'].isin(conversion_metrics)]

# Take latest Date per cell
max_dates = df.groupby('cell_name')['Date'].max()
df = df[df['Date'].isin(max_dates)]

# ------------------------
# Build results table for Bayesian posterior
# ------------------------
alpha_prior = 1.0
beta_prior = 1.0
results_rows = []

for objective in df['conversion_segment'].unique():
    obj_df = df[df['conversion_segment'] == objective]
    for dt in obj_df['analysis_date'].unique():
        dt_df = obj_df[obj_df['analysis_date'] == dt]
        for idx, r in dt_df.iterrows():
            conversions = int(r.get('treatment_conversions', 0) or 0)
            users = int(r.get('treatment_user_count', 0) or 0)
            users = users if users > 0 else 1

            results_rows.append({
                'dt': dt,
                'cell': r.get('study_name', f'Cell_{idx}'),
                'metric': objective,
                'conversions': conversions,
                'population_test': users,
                'impressions': r.get('impressions', 0),
                'cps': r.get('cps', 0)
            })

results = pd.DataFrame(results_rows) if results_rows else pd.DataFrame()

compare_on = st.selectbox('Comparison metric for winning probability:', 
                          options=['conversion_rate', 'conversions'])

# Clear cached results if compare_on changes
if "last_compare_on" not in st.session_state:
    st.session_state.last_compare_on = compare_on

if st.session_state.last_compare_on != compare_on:
    for k in list(st.session_state.keys()):
        if k.startswith(("ci_", "density_")):
            del st.session_state[k]
    st.session_state.last_compare_on = compare_on


win_prob_df, samples_df = compute_win_probabilities(results, n_sims, compare_on=compare_on)
freq_df = add_frequentist_stats(win_prob_df, compare_on=compare_on)
win_prob_df = win_prob_df.merge(freq_df, on=['dt', 'cell', 'metric'], how='left')

# Display summary table
st.subheader('[Winning Probability Summary](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) ')
summary_table = win_prob_df[['cell', 'metric', 'users', 'impressions', 'cps','win_prob', 'lift_vs_zero', 'ci_low', 'ci_high', 'p_value']]
summary_table = summary_table.rename(columns={'cell': 'Cell', 
                                              'users': 'users_reached',
                                              'cps': 'CPS',
                                              'win_prob': 'Winning Probability'})
# add , to users_reached and impressions
summary_table['users_reached'] = summary_table['users_reached'].apply(lambda x: f"{x:,}")
summary_table['impressions'] = summary_table['impressions'].apply(lambda x: f"{x:,}")

# format lift_vs_zero, ci_low/high: if conversions, then 0 decimal places; if conversion_rate, then percentage
if compare_on == 'conversion_rate':
    summary_table['lift_vs_zero'] = summary_table['lift_vs_zero'].apply(lambda x: f"{x:.3%}")
    summary_table['ci_low'] = summary_table['ci_low'].apply(lambda x: f"{x:.3%}")
    summary_table['ci_high'] = summary_table['ci_high'].apply(lambda x: f"{x:.3%}")
else:
    summary_table['lift_vs_zero'] = summary_table['lift_vs_zero'].apply(lambda x: f"{x:.0f}")
    summary_table['ci_low'] = summary_table['ci_low'].apply(lambda x: f"{x:.0f}")
    summary_table['ci_high'] = summary_table['ci_high'].apply(lambda x: f"{x:.0f}")

summary_table['p_value'] = summary_table['p_value'].apply(lambda x: f"{x:.3f}" if pd.notnull(x) else 'N/A')

summary_table['Winning Probability'] = summary_table['Winning Probability'].apply(lambda x: f"{x:.1%}")
st.write(summary_table.set_index('Cell'))

# ---- cache CSVs ----
if "win_prob_csv" not in st.session_state:
    st.session_state["win_prob_csv"] = win_prob_df.to_csv(index=False).encode("utf-8")

if "samples_csv" not in st.session_state:
    st.session_state["samples_csv"] = samples_df.to_csv(index=False).encode("utf-8")

# ---- download buttons ----
st.download_button(
    "Download Winning Probability Summary CSV",
    data=st.session_state["win_prob_csv"],
    file_name="winning_probability_summary.csv",
    mime="text/csv"
)

st.download_button(
    "Download Posterior Samples CSV",
    data=st.session_state["samples_csv"],
    file_name="posterior_samples.csv",
    mime="text/csv"
)

# -----------------------------
# CI / Error Bar Plot
# -----------------------------
st.subheader('[Confidence Intervals](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')
import matplotlib.ticker as mtick

if not win_prob_df.empty:
    for metric in win_prob_df['metric'].unique():
        df_metric = win_prob_df[win_prob_df['metric'] == metric].copy()
        if df_metric.empty:
            continue

        # Determine plotting values based on metric
        if compare_on == 'conversion_rate':
            y_vals = df_metric['conversion_rate']
            y_label = 'Conversion Rate'
            is_percentage = True
        elif compare_on == 'impressions':
            y_vals = df_metric['impressions']
            y_label = 'Impressions'
            is_percentage = False
        elif compare_on == 'reach':
            y_vals = df_metric['users']
            y_label = 'Reach'
            is_percentage = False
        else:  # raw conversions
            y_vals = df_metric['conversions']
            y_label = 'Conversions'
            is_percentage = False

        # Use CI from freq_df
        df_metric['ci_low'] = df_metric['ci_low'].fillna(y_vals)
        df_metric['ci_high'] = df_metric['ci_high'].fillna(y_vals)

        # Compute min/max for y-axis
        y_min = df_metric['ci_low'].min() * 0.95
        y_max = df_metric['ci_high'].max() * 1.05

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.errorbar(
            x=df_metric['cell'],
            y=y_vals,
            yerr=[y_vals - df_metric['ci_low'], df_metric['ci_high'] - y_vals],
            fmt='o',
            ecolor='green',
            capsize=5,
            capthick=2
        )
        ax.set_ylabel(y_label, fontsize=12)
        ax.set_ylim(y_min, y_max)
        ax.set_xticks(range(len(df_metric['cell'])))
        ax.set_xticklabels(df_metric['cell'], rotation=45)

        if is_percentage:
            ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
        plt.title(f"{metric} - CI/Error Bar", fontsize=14)
        st.pyplot(fig)

# ---- cache CI figure ----
ci_key = f"ci_{metric}_{compare_on}"
cache_figure(fig, ci_key)

# ---- download buttons ----
if f"{ci_key}_png" in st.session_state:
    st.download_button(
        f"Download CI ({metric}) PNG",
        data=st.session_state[f"{ci_key}_png"],
        file_name=f"{metric}_ci_{compare_on}.png",
        mime="image/png"
    )

if f"{ci_key}_pdf" in st.session_state:
    st.download_button(
        f"Download CI ({metric}) PDF",
        data=st.session_state[f"{ci_key}_pdf"],
        file_name=f"{metric}_ci_{compare_on}.pdf",
        mime="application/pdf"
    )


# -----------------------------
# Density Plot
# -----------------------------
st.subheader('[Density Plots (Posterior Samples)](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')
sns.set_context('talk')
sns.set_style('darkgrid')

density_rows = []
for (dt, metric), group in win_prob_df.groupby(['dt', 'metric']):
    cells = group['cell'].tolist()
    for cell in cells:
        # Use posterior samples if available
        s = samples_df[(samples_df['date'] == dt) & 
                       (samples_df['metric'] == metric) & 
                       (samples_df['cell'] == cell)]['metric_samples'].to_numpy()

        # If single value (absolute metrics), add small jitter for KDE plotting
        if s.size <= 1:
            s = np.repeat(s, n_sims) if s.size == 1 else np.full(n_sims, 0)
            s = s + np.random.normal(0, 0.01 * max(s.max(), 1), size=n_sims)

        density_rows.append(pd.DataFrame({
            'date': dt,
            'cell': cell,
            'metric': metric,
            'value': s
        }))

if density_rows:
    density_df = pd.concat(density_rows, ignore_index=True)

    # Adjust KDE plots for each metric
    for metric in density_df['metric'].unique():
        df_metric = density_df[density_df['metric'] == metric]
        fig, ax = plt.subplots(figsize=(10, 4))
        for cell in df_metric['cell'].unique():
            sns.kdeplot(df_metric[df_metric['cell'] == cell]['value'], ax=ax, shade=True, label=cell)
        ax.set_xlabel(compare_on.capitalize())
        ax.set_ylabel('Density')
        # Set y-limits to match data range
        # y_min = df_metric['value'].min() * 0.95
        # y_max = df_metric['value'].max() * 1.05
        # ax.set_xlim(y_min, y_max)
        if compare_on == 'conversion_rate':
            ax.xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
        ax.legend(title='Cells')
        plt.title(f"{metric} - Density Plot", fontsize=14)
        st.pyplot(fig)
else:
    st.write('No samples available to plot density for the selected metric.')

# ---- cache density figure ----
density_key = f"density_{metric}_{compare_on}"
cache_figure(fig, density_key)

# ---- download buttons ----
if f"{density_key}_png" in st.session_state:
    st.download_button(
        f"Download Density ({metric}) PNG",
        data=st.session_state[f"{density_key}_png"],
        file_name=f"{metric}_density_{compare_on}.png",
        mime="image/png"
    )

if f"{density_key}_pdf" in st.session_state:
    st.download_button(
        f"Download Density ({metric}) PDF",
        data=st.session_state[f"{density_key}_pdf"],
        file_name=f"{metric}_density_{compare_on}.pdf",
        mime="application/pdf"
    )
