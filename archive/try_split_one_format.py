#Import packages
import matplotlib
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from scipy.stats import beta
from scipy.stats import norm
import seaborn as sns
from io import BytesIO
from datetime import datetime


#Set Title
st.title('Winning Probability App for Evaluating D+ & Hulu Media Tests')

## Functions

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

        if n_cells < 2:
            continue

        # ---- Sample posteriors ----
        theta_samples = np.vstack([
            rng.beta(
                alpha_prior + sub.loc[i, 'conversions'],
                beta_prior + sub.loc[i, 'population_test'] - sub.loc[i, 'conversions'],
                size=n_sims
            )
            for i in range(n_cells)
        ])

        # ---- Choose comparison metric ----
        if compare_on == 'conversion_rate':
            score_samples = theta_samples

        elif compare_on == 'cps':
            # CPS = spend / (users * CVR)
            spend = sub['spend'].values[:, None]
            users = sub['population_test'].values[:, None]
            score_samples = spend / (users * theta_samples)
            score_samples = np.where(score_samples <= 0, np.inf, score_samples)

            # lower CPS is better → flip sign
            score_samples = -score_samples

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
                'cps': sub.loc[i, 'cps'],
                'users': sub.loc[i, 'population_test'],
                'conversions': sub.loc[i, 'conversions'],
                'conversion_rate': sub.loc[i, 'conversions'] / sub.loc[i, 'population_test']
            })

            samples_rows.append(pd.DataFrame({
                'date': dt,
                'cell': sub.loc[i, 'cell'],
                'metric': metric,
                'conversion_rate_samples': theta_samples[i],
                'spend': sub.loc[i, 'spend'],
                'population_test': sub.loc[i, 'population_test']
            }))

    win_prob_df = pd.DataFrame(win_prob_rows)
    samples_df = pd.concat(samples_rows, ignore_index=True)

    samples_df['cps_samples'] = (
        samples_df['spend'] /
        (samples_df['population_test'] * samples_df['conversion_rate_samples'].replace(0, np.nan))
    )

    return win_prob_df, samples_df


def add_frequentist_stats(win_prob_df, baseline_cell=None, compare_on='conversion_rate'):
    """
    Add frequentist statistics: p-value and confidence intervals.

    If `baseline_cell` is provided, comparisons are computed against that cell.
    Otherwise the first cell in each (dt,metric) group is used as baseline.
    """
    out = []

    for (dt, metric), sub in win_prob_df.groupby(['dt', 'metric']):
        sub = sub.reset_index(drop=True)

        if baseline_cell:
            # try to find baseline row by cell name
            base_rows = sub[sub['cell'] == baseline_cell]
            if not base_rows.empty:
                baseline = base_rows.iloc[0]
            else:
                baseline = sub.iloc[0]
        else:
            baseline = sub.iloc[0]

        if compare_on == 'conversion_rate':
            p0 = baseline.get('conversion_rate', baseline.get('win_prob', np.nan))
        elif compare_on == 'reach':
            p0 = baseline.get('reach', baseline.get('win_prob', np.nan))
        else:
            p0 = baseline.get('win_prob', np.nan)
        n0 = baseline.get('users', baseline.get('population', np.nan))
        x0 = baseline.get('conversions', np.nan)

        for i, r in sub.iterrows():
            if compare_on == 'conversion_rate':
                p = r.get('conversion_rate', r.get('win_prob', np.nan))
            elif compare_on == 'reach':
                p = r.get('reach', r.get('win_prob', np.nan))
            else:
                p = r.get('win_prob', np.nan)
            n = r.get('users', r.get('population', np.nan))
            x = r.get('conversions', np.nan)

            # Confidence interval for single proportion
            ci_low = np.nan
            ci_high = np.nan
            p_value = np.nan
            lift = np.nan

            if n and not np.isnan(p):
                se = np.sqrt(p * (1 - p) / n)
                z = norm.ppf(0.975)
                ci_low = p - z * se
                ci_high = p + z * se

            # pairwise test vs baseline if baseline has counts
            if i == 0 and (baseline_cell is None):
                p_value = np.nan
                lift = 0.0
            else:
                try:
                    pooled = (x + x0) / (n + n0)
                    se_diff = np.sqrt(pooled * (1 - pooled) * (1.0 / n + 1.0 / n0))
                    if se_diff > 0:
                        z_stat = (p - p0) / se_diff
                        p_value = 2 * (1 - norm.cdf(abs(z_stat)))
                        lift = p - p0
                except Exception:
                    p_value = np.nan
                    lift = np.nan

            out.append({
                'dt': dt,
                'cell': r['cell'],
                'metric': metric,
                'lift_vs_baseline': lift,
                'ci_low': ci_low,
                'ci_high': ci_high,
                'p_value': p_value
            })

    return pd.DataFrame(out)


"""
This app calculates the winning probability of cells in split tests we run with our media vendors.
This methodology is based on Hulu's proprietary winning probability framework.
See [here](https://docs.google.com/document/d/1XgL30F5GybUdpCsJemZ0kCmOeFwRZDxizqZFM9dJpu8/edit?tab=t.0) for App Documentation, or reach out to Max Wilson or Shirley Deng on the BLADE team at maxim.wilson@disney.com or shirley.deng@disney.com for more information.
"""


st.subheader('Test Parameters')
"""
See [here](https://docs.google.com/spreadsheets/d/1XCZSbQNNYVPRl7AEICgsLKCGi-Re_Owk/edit?gid=1708648830#gid=1708648830) for an input template with the correct format.
"""
# ##insert a button with the options for vendors
# test_type = st.radio('Select the media partner from the options below:',('Facebook','YouTube','Snapchat','The Trade Desk','Gemini','Roku'))

##if the user clicks facebook or youtube or tradedesk, run the code below
##if the user clicks a vendor that is not facebook or youtube or the trade desk, print 'functionality for that vendor is coming soon'
# if test_type not in ('Facebook','YouTube','The Trade Desk'):
#     st.write('Functionality for that vendor is coming soon.')
#     st.stop()

##add a button that allows the user to upload the test data as a csv or an excel file
##if the user clicks the button, open up a dialog box that allows the user to browse their computer and select the file
##also allow the user to drag and drop the file into the app

input_file = st.file_uploader('Upload Test Data as a csv or an excel file:', type=['csv', 'xlsx'])

#Read in data from the file the user uploaded
##if the user uploaded an excel file, read the file into a dataframe called raw
##if the user uploaded a csv file, read the file into a dataframe called raw
##if the user uploaded a file that is not a csv or an excel file, print 'please upload a csv or an excel file'
if input_file is None:
    st.stop()
elif input_file.name.endswith('.xlsx'):
    raw = pd.read_excel(input_file)
    if raw.columns[0] != 'cell_name':
            st.write('INCORRECT FORMAT: Please upload a file in the correct format for The Trade Desk. See [here](https://google.com) for details on getting the data in the correct format.')
            st.stop()
elif input_file.name.endswith('.csv'):
    raw = pd.read_csv(input_file,header=None)
else:
    st.write('Please upload a csv or an xlsx file.')
    st.stop()



##add a slider that allows the user to selet the number of simulations to run
##the key for the slider is num_simulations
##the default value is 5000
##the minimum value is 1000 and the maximum value is 100000
n_sims = st.slider('Select the number of simulations to run (more simulations will give more stable results, but takes longer):', 1000, 100000, 5000)

## create a dataframe called df that is a copy of raw
## if the test_type is facebook, pivot the data
df = raw.copy()


##standardize the data based on the vendor
##set column values to be numberic for columns spend, conversions_incremental, conversions_incremental_upper, conversions_confidence, conversions_test, conversions_control_scaled, population_test, population_control
## some of t]=datetime.now().strftime('%Y-%m-%d')

# df['absolute_lift']=df['Absolute_lift']
df['treatment_cvr']=df['test_conv_rate']
df['cps'] = df['CPS']
df['cps'] = pd.to_numeric(df['cps'])
df['conversion_segment']=df['event_type']
df['experiment_cost_usd']=df['spend_usd']
df['treatment_cvr_confidence_level']=df['confidence_level']
df['treatment_user_count']=df['n_test']
# df['control_user_count']=df['n_control']
df['study_name']=df['cell_name']
df['treatment_conversions']=df['test_conversions']
# df['control_conversions']=df['control_conversions']
##create a column called absolutelift_CI that is the absolute lift confidence interval
##derive the absolute lift confidence interval from the absolute lift confidence level
##get the z score for the absolute lift confidence level
##add the z score to the dataframe
df['z_score'] = norm.ppf(df['treatment_cvr_confidence_level'])
##find the standard error of the absolute lift
#df['phat'] = (df['treatment_conversions']+df['control_conversions'])/(df['treatment_user_count']+df['control_user_count'])
#df['se']= df['phat']*(1-df['phat'])/ (df['treatment_user_count']+df['control_user_count'])
#df['standard_error'] =  (df['se']).sqrt()
df['standard_error'] = df['treatment_cvr']/df['z_score']
##create the absolute lift confidence interval column based on the standard error and the z score for 90% confidence
df['treatment_cvr_CI'] = df['standard_error']*norm.ppf(0.90)
df['treatment_cvr_CI'] = df['treatment_cvr_CI'].abs()
##df['absolutelift_CI'] = df['standard_error']*norm.ppf(0.90)

##legacy code for date
df['analysis_date']=datetime.now().strftime('%Y-%m-%d')


### in the df dataframe, if the conversions incremental is 0, change it to equal to 1
# df['absolute_lift'] = df['absolute_lift'].replace(0,1)

##add buttons to the app that allows the user to select one or more items the list of available conversion metrics
## The conversion metrics are the unique values in the objective_name column in df
## The conversion metrics are sorted in alphabetical order
## allow the user to select more than one conversion metric
## the key for the buttons is conversion_metrics
## default is all that none are selected
conversion_metrics = st.multiselect('Select at least one conversion metric to be analyzed:', sorted(df['conversion_segment'].unique()))

# Track whether a run has been requested and persist results across reruns (downloads)
if 'run_requested' not in st.session_state:
    st.session_state['run_requested'] = False

if st.button('Run Analysis'):
    # mark run requested and clear any prior results so a fresh compute happens
    st.session_state['run_requested'] = True
    for _k in ('win_prob_df', 'samples_df', 'fig2_png', 'fig2_pdf'):
        if _k in st.session_state:
            del st.session_state[_k]
    
#if conversion_metrics, test_type, and input_file are not empty, allow the user to click a button that says 'Run Analysis'
##otherwise, print 'Please select a conversion metric, test vendor, and upload a file'
##only run the code below if the user clicks the 'Run Analysis' button
if conversion_metrics and input_file is not None:
    st.write('Ready to Go!')
    ##continue the code if the user clicks a Run Analysis button and the export_as_pdf variable is empty or if the user clicks the export as pdf button
    if st.session_state.get('run_requested'):
        ## add a line separator to the app
        st.markdown('---')
    else:
        st.stop()
else:
    st.write('Please select at least one conversion metric.')
    ##stop the code from running below to prevent errors from displaying
    st.stop()


##write test_name to the app as a subheader
st.subheader('Test Name')

##create a variable test_name
test_name = input_file.name.split('.')[0]

st.write(test_name)

##write the topline metrics to the app as a subheader
st.subheader('Media Metrics')

##create a dataframe called per_cell_metrics
per_cell_metrics = df.groupby('cell_name')[['experiment_cost_usd','n_test']].mean()


###create a dataframe with topline metrics for the test
##the spend value is the sum of the spend column in the per_cell_metrics dataframe rounded
##the impressions value is the sum of the impressions column in the per_cell_metrics dataframe rounded
topline_metrics = pd.DataFrame({'Metric Name':['Cells','Spend (USD)','Reach'],
                                    'Metric Value':[round(per_cell_metrics.shape[0]),
                                                    round(per_cell_metrics['experiment_cost_usd'].sum()),
                                                    round(per_cell_metrics['n_test'].sum())]})




# CSS to inject contained in a string
hide_table_row_index = """
            <style>
            thead tr th:first-child {display:none}
            tbody th {display:none}
            </style>
            """

# Inject CSS with Markdown
st.markdown(hide_table_row_index, unsafe_allow_html=True)
##For values above 1000, add a comma to the value
topline_metrics['Metric Value'] = topline_metrics['Metric Value'].apply(lambda x: '{:,}'.format(x))
##For the only the spend row, add a dollar sign to the metric value
topline_metrics['Metric Value'][1] = '$' + topline_metrics['Metric Value'][1]

##write the topline metrics to the app as a table
st.table(topline_metrics)



## reduce df to only the rows where the value of conversion_segment is in the list conversion_metrics
## write a function that returns True if the value of conversion_segment is in the list conversion_metrics
def conversion_segment_filter(x):
    if x in conversion_metrics:
        return True
    else:
        return False
## apply the conversion_segment_filter function to the conversion_segment column in df
df = df[df['conversion_segment'].apply(conversion_segment_filter)]


##find the max values of the Date column in df for each cell_name
max_dates = df.groupby('cell_name')['Date'].max()
##reduce dataframe to only the rows where the date column is the max value in the date column for each cell_name
df = df[df['Date'].isin(max_dates)]


## Reduce to only useful columns
useful_columns = ['analysis_date',
                  'study_name',
                  'treatment_user_count',
                #   'control_user_count',
                  'treatment_conversions',
                #   'control_conversions',
                  'experiment_cost_usd',
                  'cps',
                  'conversion_segment',
                  'treatment_cvr_confidence_level'
                 ]

metrics_df = df[useful_columns]

## reduce metrics_df to only the rows where the value of conversion_segment is in the list conversion_metrics
## apply the previously-defined `conversion_segment_filter` to `metrics_df`
metrics_df = metrics_df[metrics_df['conversion_segment'].apply(conversion_segment_filter)]


## set seed
np.random.seed(1234)

# Use weak prior (Beta(1,1)) for per-cell conversion rates - more stable i think
alpha_prior = 1.0
beta_prior = 1.0


# Build one `results` table with per-cell Beta posteriors
results_rows = []
for objective in metrics_df['conversion_segment'].unique():
    obj_df = metrics_df[metrics_df['conversion_segment'] == objective]
    for dt in obj_df['analysis_date'].unique():
        dt_df = obj_df[obj_df['analysis_date'] == dt]
        for idx, r in dt_df.iterrows():
            conversions = int(r.get('treatment_conversions', 0) or 0)
            users = int(r.get('treatment_user_count', 0) or 0)
            # avoid degenerate users=0
            users = users if users > 0 else 1

            alpha_post = alpha_prior + conversions
            beta_post = beta_prior + users - conversions

            results_rows.append({
                'dt': dt,
                'cell': r.get('study_name') or r.get('cell_name') or f'Cell_{idx}',
                'metric': objective,
                'cell_alpha_posterior': alpha_post,
                'cell_beta_posterior': beta_post,
                'conversions': conversions,
                'population_test': users,
                'cps': r.get('cps', np.nan),
                'spend': r.get('experiment_cost_usd') or r.get('spend_usd') or 0
            })

results = pd.DataFrame(results_rows) if results_rows else pd.DataFrame()

## Let user choose comparison metric used for win-prob and p-values
compare_on = st.selectbox('Comparison metric for winning probability and p-values',
                          options=['conversion_rate', 'reach'],
                          index=0,
                          help='Select which observed metric to compare when computing win probabilities and frequentist p-values.')

# Compute winning probabilities and posterior samples (recompute when compare_on or n_sims changes)
if ('win_prob_df' in st.session_state and 'samples_df' in st.session_state
        and st.session_state.get('last_compare_on') == compare_on
        and st.session_state.get('last_n_sims') == n_sims):
    win_prob_df = st.session_state['win_prob_df']
    samples_df = st.session_state['samples_df']
else:
    win_prob_df, samples_df = compute_win_probabilities(results, n_sims, compare_on=compare_on)
    st.session_state['win_prob_df'] = win_prob_df
    st.session_state['samples_df'] = samples_df
    st.session_state['last_compare_on'] = compare_on
    st.session_state['last_n_sims'] = n_sims

# Allow user to pick a baseline cell for frequentist comparisons
baseline_options = ['(first row)'] + sorted(win_prob_df['cell'].unique()) if not win_prob_df.empty else ['(first row)']
baseline_choice = st.selectbox('Baseline for frequentist comparisons', baseline_options)
baseline_cell = None if baseline_choice == '(first row)' else baseline_choice

# add frequentist stats like p-value and CI using selected baseline
freq_df = add_frequentist_stats(win_prob_df, baseline_cell=baseline_cell, compare_on=compare_on)
win_prob_df = win_prob_df.merge(freq_df, on=['dt','cell','metric'], how='left')


###add subheader that displays topline results
## include a link for the word "winning probability" that links to the bottom of the page where "Explanation of Winning Probability" is displayed
## include a link for the word "CPiS" that links to the bottom of the page where "Explanation of CPiS" is displayed (removed)
st.subheader('[Winning Probability](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) ')
summary_table = win_prob_df[['dt','cell','metric','win_prob','cps','p_value']]
##change the name of the column win_prob to Winning Probability
summary_table = summary_table.rename(columns = {'win_prob': 'Winning Probability'})
##change the name of the column cps to CPS
summary_table = summary_table.rename(columns = {'cps': 'CPS'})
##change the name of the column cell to Cell
summary_table = summary_table.rename(columns = {'cell': 'Cell'})

##create a new table that is the summary table but without the dt column
##call the new table to_view_2
to_view_2 = summary_table.drop(columns = ['dt'])

## format the values in Winning Probability column in to_view_2 to be percentages with one decimal place
to_view_2['Winning Probability'] = to_view_2['Winning Probability'].apply(lambda x: '{:.1%}'.format(x))
## format the values in CPS column in to_view_2 to be currency with no decimal places
##currency is dollars
to_view_2['CPS'] = to_view_2['CPS'].apply(lambda x: '${:,.0f}'.format(x))

## display the df to_view_2 in the app with no index
st.write(to_view_2.set_index('Cell'))





confidence_interval_explanation = """
Confidence Intervals are a way to measure the uncertainty of a statistic.
"""

###add subheader for the confidence intervals
st.subheader('[Confidence Intervals](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')
##add an expander to the app
##the expander will display the text in the variable confidence_interval_explanation
##expander = st.expander("What is a Confidence Interval?")

#plot confidence intervals --> Copied directly from Google
sns.set_style('darkgrid')


# Posterior-based conversion-rate lift vs baseline (errorbar summary)
if compare_on == 'conversion_rate' and not samples_df.empty and not win_prob_df.empty:
    sns.set_context('poster')
    posterior_lift_rows = []
    for (dt, metric), group in win_prob_df.groupby(['dt', 'metric']):
        cells = group['cell'].tolist()
        base = baseline_cell if (baseline_cell in cells) else cells[0]

        # collect samples for each cell
        cell_samples = {}
        for cell in cells:
            s = samples_df[(samples_df['date'] == dt) & (samples_df['metric'] == metric) & (samples_df['cell'] == cell)]['conversion_rate_samples'].to_numpy()
            if s.size == 0:
                s = np.zeros(n_sims)
            cell_samples[cell] = s

        base_samples = cell_samples.get(base, np.zeros(n_sims))

        for cell in cells:
            lift_s = cell_samples[cell] - base_samples
            median = np.median(lift_s)
            ci_low, ci_high = np.percentile(lift_s, [2.5, 97.5])
            prob_gt0 = float((lift_s > 0).mean())
            posterior_lift_rows.append({'dt': dt, 'cell': cell, 'metric': metric,
                                        'median': median, 'ci_low': ci_low, 'ci_high': ci_high,
                                        'prob_gt0': prob_gt0})

    posterior_lift_df = pd.DataFrame(posterior_lift_rows)

    for obj in posterior_lift_df['metric'].unique():
        pl = posterior_lift_df[posterior_lift_df['metric'] == obj].reset_index(drop=True)
        if pl.empty:
            continue
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.tick_params(axis='x', rotation=45, labelsize=12, pad=-10)
        ax.tick_params(axis='y', labelsize=13)

        x = np.arange(len(pl))
        med = pl['median'].values
        lower_err = med - pl['ci_low'].values
        upper_err = pl['ci_high'].values - med
        ax.errorbar(x, med, yerr=[lower_err, upper_err], fmt='o', ecolor='g', capthick=2)
        ax.axhline(0, color='r', linestyle='--')
        ax.set_xticks(x)
        ax.set_xticklabels(pl['cell'].values, rotation=45)
        ax.set_ylabel('Lift vs baseline (percentage points)', fontsize=12)
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1.0))
        plt.title(obj, fontsize=15)

        for xi, row in pl.iterrows():
            ax.text(xi, row['median'], f"  P>0={row['prob_gt0']:.1%}", va='bottom', fontsize=9)

        plt.show()
        st.write(fig)
else:
    # If conversion-rate samples aren't available, show vendor absolute_lift if present
    for obj in df['conversion_segment'].unique():
        sub_df = df[df['conversion_segment'] == obj]
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.tick_params(axis='x', rotation=45, labelsize=12, pad=-10)
        ax.tick_params(axis='y', labelsize=13)
        plt.errorbar(x=np.array(sub_df.get('study_name', sub_df.get('cell_name'))),
                     y=np.array(sub_df.get('absolute_lift', np.zeros(len(sub_df)))),
                     yerr=np.array(sub_df.get('absolutelift_CI', np.zeros(len(sub_df)))),
                     fmt='o', ecolor='g', capthick=2)
        ax.axhline(y=0, color='r', linestyle='--')
        plt.title(obj, fontsize=15)
        ax.set_ylabel('Incremental Conversions', fontsize=12)
        plt.show()
        st.write(fig)
    st.write(fig)



## Add density plots of posterior lift vs baseline
st.subheader('[Density Plots (Lift vs baseline)](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')
sns.set()
sns.set_context('talk')
sns.set_style('darkgrid')

lift_samples_rows = []
if compare_on == 'conversion_rate' and not samples_df.empty and not win_prob_df.empty:
    for (dt, metric), group in win_prob_df.groupby(['dt', 'metric']):
        cells = group['cell'].tolist()
        base = baseline_cell if (baseline_cell in cells) else cells[0]

        cell_samples = {}
        for cell in cells:
            s = samples_df[(samples_df['date'] == dt) & (samples_df['metric'] == metric) & (samples_df['cell'] == cell)]['conversion_rate_samples'].to_numpy()
            if s.size == 0:
                s = np.zeros(n_sims)
            cell_samples[cell] = s

        base_samples = cell_samples.get(base, np.zeros(n_sims))

        for cell in cells:
            lift_s = cell_samples[cell] - base_samples
            lift_samples_rows.append(pd.DataFrame({
                'date': dt,
                'cell': cell,
                'metric': metric,
                'lift_samples': lift_s
            }))

    if lift_samples_rows:
        lift_samples_df = pd.concat(lift_samples_rows, ignore_index=True)
    else:
        lift_samples_df = pd.DataFrame(columns=['date','cell','metric','lift_samples'])

    grid = sns.FacetGrid(lift_samples_df[['date','cell','metric','lift_samples']],
                         row='metric', hue='cell', height=3.5, aspect=2)
    grid.map(sns.kdeplot, 'lift_samples', shade=True)
    grid.set_titles(row_template="{row_name}")
    grid.add_legend(title='Cells')
    grid.set_axis_labels('Lift vs baseline (percentage points)', 'Density')

    fig2 = grid.fig
    # `fig2.axes` may be a list; ensure we can flatten reliably
    for ax in np.array(fig2.axes).flatten():
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1.0))
        ax.axvline(0, color='r', linestyle='--')

    st.pyplot(fig2)
else:
    st.write('No lift samples available to plot densities for the selected metric.')

# Save figure bytes to session_state so downloads don't force recompute or disappear
if 'fig2_png' not in st.session_state or 'fig2_pdf' not in st.session_state:
    try:
        _buf = BytesIO()
        fig2.savefig(_buf, format='png', bbox_inches='tight')
        _buf.seek(0)
        st.session_state['fig2_png'] = _buf.getvalue()

        _buf2 = BytesIO()
        fig2.savefig(_buf2, format='pdf', bbox_inches='tight')
        _buf2.seek(0)
        st.session_state['fig2_pdf'] = _buf2.getvalue()
    except Exception:
        pass
# Provide download buttons for the density figure and CSV exports
try:
    buf = BytesIO()
    fig2.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    st.download_button('Download density (PNG)', data=buf.getvalue(), file_name=f"{test_name}_density.png", mime='image/png')

    buf_pdf = BytesIO()
    fig2.savefig(buf_pdf, format='pdf', bbox_inches='tight')
    buf_pdf.seek(0)
    st.download_button('Download density (PDF)', data=buf_pdf.getvalue(), file_name=f"{test_name}_density.pdf", mime='application/pdf')
except Exception:
    # If figure saving fails, continue without blocking the app
    pass

# CSV exports for results and samples
if 'win_prob_df' in globals() and not win_prob_df.empty:
    csv = win_prob_df.to_csv(index=False).encode('utf-8')
    st.download_button('Download win_prob CSV', data=csv, file_name=f"{test_name}_win_prob.csv", mime='text/csv')

if 'samples_df' in globals() and not samples_df.empty:
    csv2 = samples_df.to_csv(index=False).encode('utf-8')
    st.download_button('Download samples CSV', data=csv2, file_name=f"{test_name}_samples.csv", mime='text/csv')
