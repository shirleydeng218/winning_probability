#Import packages
import math
import os
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


#Set Title
st.title('Winning Probability App for Split Tests')


"""
This app calculates the winning probability of cells in split tests.
It uses Bayesian analysis to sample from posterior conversion rate distributions per cell,
then determines which cell is most likely to have the best performance.
    """Parse/validate a standardized DataFrame and return a reduced metrics_df.

    This mirrors the script's existing column-selection and basic filtering
    so downstream code can consume a consistent `metrics_df`.
    """
    useful_columns = ['analysis_date',
                      'study_name',
                      'treatment_user_count',
                      'control_user_count',
                      'treatment_conversions',
                      'control_conversions',
                      'experiment_cost_usd',
                      'cpis',
                      'conversion_segment',
                      'absolute_lift_confidence_level'
                     ]

    metrics_df = df.copy()
    # Safely select only columns that exist
    available = [c for c in useful_columns if c in metrics_df.columns]
    metrics_df = metrics_df[available].copy()

    # Filter conversion segments
    if 'conversion_segment' in metrics_df.columns and conversion_metrics:
        metrics_df = metrics_df[metrics_df['conversion_segment'].isin(conversion_metrics)].copy()

    # Vendor-specific reductions (keeps original behavior)
    if vendor == 'YouTube' and 'analysis_day_string' in df.columns:
        metrics_df = metrics_df[df['analysis_day_string'] == 'LATEST'].copy()
    if vendor == 'The Trade Desk' and 'Date' in df.columns:
        max_dates = df.groupby('cell_name')['Date'].max()
        metrics_df = metrics_df[df['Date'].isin(max_dates)].copy()

    return metrics_df


def compute_win_probabilities(results, n_sims, seed=1234):
    """Vectorized sampling for split tests: compute per-cell win probabilities.
    
    For each simulation, sample a conversion rate from each cell's Beta posterior,
    and count how many times each cell wins (has the highest conversion rate).

    Args:
        results: DataFrame with cell_alpha_posterior, cell_beta_posterior cols per cell.
        n_sims: int number of simulations.
    Returns:
        win_prob_df, samples_df
    """
    np.random.seed(seed)
    win_prob_df = pd.DataFrame()
    samples_df = []

    for dt in results['dt'].unique():
        for metric in results['metric'].unique():
            sub = results[(results['dt'] == dt) & (results['metric'] == metric)].reset_index(drop=True)
            if sub.shape[0] == 0:
                continue
            n_cells = sub.shape[0]

            # prepare parameter arrays for conversion rates (not lift)
            cell_a = sub['cell_alpha_posterior'].to_numpy(dtype=float)
            cell_b = sub['cell_beta_posterior'].to_numpy(dtype=float)
            conf = sub['conf_level'].to_numpy(dtype=float)

            # sample arrays: conversion rate per cell per simulation (n_cells x n_sims)
            conv_samples = np.zeros((n_cells, n_sims))

            # only sample for rows where conf_level > 0
            idx = np.where(conf > 0)[0]
            for i in idx:
                conv_samples[i, :] = np.random.beta(cell_a[i], cell_b[i], size=n_sims)

            # find winner per simulation: which cell has highest conversion rate
            winner_idx = np.argmax(conv_samples, axis=0)  # length n_sims
            wins = np.bincount(winner_idx, minlength=n_cells)
            win_prob = wins.astype(float) / float(n_sims)

            sub = sub.copy()
            sub['win_prob'] = win_prob.tolist()
            win_prob_df = pd.concat([win_prob_df, sub], ignore_index=True)

            # build samples_df entries (stacked per-cell)
            for i in range(n_cells):
                samples_df.append(pd.DataFrame({
                    'date': np.repeat(dt, n_sims),
                    'cell': np.repeat(sub.loc[i, 'cell'], n_sims),
                    'metric': np.repeat(metric, n_sims),
                    'spend': np.repeat(sub.loc[i, 'spend'], n_sims),
                    'population_test': np.repeat(sub.loc[i, 'population_test'], n_sims),
                    'conversion_rate_samples': conv_samples[i, :]
                }))

    if samples_df:
        samples_df = pd.concat(samples_df, ignore_index=True)
        # for split tests, compute CPCS (cost per converted sign-up) = spend / (pop * conversion_rate)
        samples_df['cpcs_samples'] = samples_df['spend'] / (samples_df['population_test'] * samples_df['conversion_rate_samples'].replace({0: np.nan}))
    else:
        samples_df = pd.DataFrame()

    return win_prob_df, samples_df


"""
This app calculates the winning probability of cells in incrementality tests we run with our media vendors.
This methodology is based on Hulu's proprietary winning probability framework.
See [here](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) for more details or reach out to Max Wilson on the Hulu Marketing Analytics team at maxim.wilson@disneystreaming.com.
"""

st.write('This app compares 2-3 cell variants in a split test and calculates winning probabilities based on conversion rates.')
"""
Supported vendors: Facebook, YouTube, and The Trade Desk.
"""
st.subheader('Test Parameters')
##insert a button with the options for vendors
test_type = st.radio('Select the media partner from the options below:',('Facebook','YouTube','Snapchat','The Trade Desk','Gemini','Roku'))

##if the user clicks facebook or youtube or tradedesk, run the code below
##if the user clicks a vendor that is not facebook or youtube or the trade desk, print 'functionality for that vendor is coming soon'
if test_type not in ('Facebook','YouTube','The Trade Desk'):
    st.write('Functionality for that vendor is coming soon.')
    st.stop()

##add a button that allows the user to upload the test data as a csv or an excel file
##if the user clicks the button, open up a dialog box that allows the user to browse their computer and select the file
##also allow the user to drag and drop the file into the app

input_file = st.file_uploader('Upload Test Data as a csv or an excel file:', type=['csv', 'xlsx'])

#Read in data from the file the user uploaded
##if the user uploaded an excel file, read the file into a dataframe called raw
##if the user uploaded a csv file, read the file into a dataframe called raw
##if the user uploaded a file that is not a csv or an excel file, print 'please upload a csv or an excel file'
if test_type in ('Facebook','YouTube','The Trade Desk'):
    if input_file is None:
        st.stop()
    elif input_file.name.endswith('.xlsx'):
        if test_type == 'Facebook':
            ## if the test type is facebook, read the first sheet sheet but with no header
            ## if the test type is not facebook, read the first sheet with a header
            raw = pd.read_excel(input_file,header=None)
            ##if the first value in the first row is 'study_name', then the file is in the correct format
            ##if not, print 'please upload a file in the correct format'
            if raw.iloc[0,0] != 'study_name':
                st.write('INCORRECT FORMAT: Please upload a file in the correct format for Facebook. See [here](https://google.com) for details on getting the data in the correct format.')
                st.stop()
        elif test_type == 'YouTube':
            raw = pd.read_excel(input_file)
            ## if the first column is 'study_id', then the file is in the correct format
            ## if not, print 'please upload a file in the correct format'
            if raw.columns[0] != 'study_id':
                st.write('INCORRECT FORMAT: Please upload a file in the correct format for YouTube. See [here](https://google.com) for details on getting the data in the correct format.')
                st.stop()
        ##if the test type is trade desk
        ##if the first column is cell_name, then the file is in the correct format
        ##if not, print 'please upload a file in the correct format'
        elif test_type == 'The Trade Desk':
            raw = pd.read_excel(input_file)
            if raw.columns[0] != 'cell_name':
                st.write('INCORRECT FORMAT: Please upload a file in the correct format for The Trade Desk. See [here](https://google.com) for details on getting the data in the correct format.')
                st.stop()
        else:
            raw = pd.read_excel(input_file)
    elif input_file.name.endswith('.csv'):
        raw = pd.read_csv(input_file,header=None)
    else:
        st.write('Please upload a csv or an xlsx file.')
        st.stop()



##add a slider that allows the user to selet the number of simulations to run
##the key for the slider is num_simulations
##the default value is 25000
##the minimum value is 1000 and the maximum value is 100000
n_sims = st.slider('Select the number of simulations to run (more simulations will give more stable results, but takes longer):', 1000, 100000, 5000)

## create a dataframe called df that is a copy of raw
## if the test_type is facebook, pivot the data
if test_type == 'Facebook':
    df = raw.T
    df.columns = df.iloc[0]
    df= df.drop(df.index[0])
    df = pd.DataFrame(df)
else:
    df = raw


##standardize the data based on the vendor
##set column values to be numberic for columns spend, conversions_incremental, conversions_incremental_upper, conversions_confidence, conversions_test, conversions_control_scaled, population_test, population_control
if test_type == 'Facebook':
    ## some of these renames are redundant, but I'm leaving them in for now
    df['spend'] = pd.to_numeric(df['spend'])
    df['conversions_incremental'] = pd.to_numeric(df['conversions_incremental'])
    df['conversions_incremental_upper'] = pd.to_numeric(df['conversions_incremental_upper'])
    df['conversions_confidence'] = pd.to_numeric(df['conversions_confidence'])
    df['conversions_test'] = pd.to_numeric(df['conversions_test'])
    df['conversions_control_scaled'] = pd.to_numeric(df['conversions_control_scaled'])
    df['population_test'] = pd.to_numeric(df['population_test'])
    df['population_control'] = pd.to_numeric(df['population_control'])
    df['population_reached'] = pd.to_numeric(df['population_reached'])
    df['impressions'] = pd.to_numeric(df['impressions'])
    ### in the df dataframe, if the conversions incremental is 0, change it to equal to 1
    df['absolute_lift']=df['conversions_incremental']
    df['cpis'] = df['spend']/df['conversions_incremental']
    df['Test_name']=df['study_name']
    df['conversion_segment']=df['objective_name']
    df['study_name']=df['cell_name']
    df['absolute_lift']=df['conversions_incremental']
    df['absolutelift_CI']=(df['conversions_incremental_upper']-df['conversions_incremental'])/2
    df['treatment_user_count']=df['population_test']
    df['control_user_count']=df['population_control']
    df['treatment_conversions']=df['conversions_test']
    df['control_conversions']=df['conversions_control_scaled']*df['population_control']/df['population_test']
    df['experiment_cost_usd']=df['spend']
    df['absolute_lift_confidence_level']=df['conversions_confidence']
    ## the below is just used to fill in a date for now
    df['analysis_date']='2022-05-19'


if test_type == 'YouTube':
    df['absolutelift_CI'] = (df['absolute_lift_ci_max']-df['absolute_lift_ci_min'])/2
    df['cpis']=df['CPiS']
    df['cpis'] = pd.to_numeric(df['cpis'])
    



if test_type == 'The Trade Desk':
    df['absolute_lift']=df['Absolute_lift']
    df['cpis'] = df['CPIS']
    df['cpis'] = pd.to_numeric(df['cpis'])
    df['conversion_segment']=df['event_type']
    df['experiment_cost_usd']=df['spend_usd']
    df['absolute_lift_confidence_level']=df['confidence_level']
    df['treatment_user_count']=df['n_test']
    df['control_user_count']=df['n_control']
    df['study_name']=df['cell_name']
    df['treatment_conversions']=df['test_conversions']
    df['control_conversions']=df['control_conversions']
    ##create a column called absolutelift_CI that is the absolute lift confidence interval
    ##derive the absolute lift confidence interval from the absolute lift confidence level
    ##get the z score for the absolute lift confidence level
    ##add the z score to the dataframe
    df['z_score'] = norm.ppf(df['absolute_lift_confidence_level'])
    ##find the standard error of the absolute lift
    #df['phat'] = (df['treatment_conversions']+df['control_conversions'])/(df['treatment_user_count']+df['control_user_count'])
    #df['se']= df['phat']*(1-df['phat'])/ (df['treatment_user_count']+df['control_user_count'])
    #df['standard_error'] =  (df['se']).sqrt()
    df['standard_error'] = df['absolute_lift']/df['z_score']
    ##create the absolute lift confidence interval column based on the standard error and the z score for 90% confidence
    df['absolutelift_CI'] = df['standard_error']*norm.ppf(0.90)
    df['absolutelift_CI'] = df['absolutelift_CI'].abs()
    ##df['absolutelift_CI'] = df['standard_error']*norm.ppf(0.90)

    ##legacy code for date
    df['analysis_date']='2022-05-19'


### in the df dataframe, if the conversions incremental is 0, change it to equal to 1
df['absolute_lift'] = df['absolute_lift'].replace(0,1)

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
if conversion_metrics and test_type and input_file is not None:
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

## if the test_type is youtube, rename the values in study_name
## study name should equal the string in the study_name column in df from the first character in the word Cell up to the end of the string
if test_type == 'YouTube':
    ##for each value in the study_name column in df
    ##if the value contains the word Cell, replace the value with the string in the study_name column in df
    # from the first character in the word Cell up the charater before "_NA"
    ## if the value does not contain "_NA", replace the value with the string from the frist character in the word Cell up to the end of the string
    for i in range(len(df['study_name'])):
        if 'Cell' in df['study_name'][i]:
            if '_NA' in df['study_name'][i]:
                df['study_name'][i] = df['study_name'][i][df['study_name'][i].find('Cell'):df['study_name'][i].find('_NA')]
            else:
                df['study_name'][i] = df['study_name'][i][df['study_name'][i].find('Cell'):]



##write test_name to the app as a subheader
st.subheader('Test Name')

##create a variable test_name
##if test_type is facebook, that is the value of the first row in the study_name column in df
if test_type == 'Facebook':
    test_name = df['Test_name'][1]
##if test_type is youtube, that is the a value derived from the first row in the study_name column in df
elif test_type == 'YouTube':
    ##test_name should equal the string in the study_name column in df from the first character up to the underscore before the word Cell
    test_name = df['study_name'][1][0:df['study_name'][1].find('_Cell')]
##if test_type is the trade desk, test_name should equal the name of the input file
elif test_type == 'The Trade Desk':
    ##without the file extension
    test_name = input_file.name.split('.')[0]

st.write(test_name)

##write the topline metrics to the app as a subheader
st.subheader('Media Metrics')

##create a dataframe called per_cell_metrics
##if test_type is facebook, the dataframe should have the following columns: cell_name, spend, impressions, reach
##the dataframe should have the following rows: the unique values in the cell_name column in df
##if test_type is youtube, the dataframe should have the following columns: cell_name, spend, reach
##the dataframe should have the following rows: the unique values in the study_name column in df
if test_type == 'Facebook':
    ##create a dataframe called per_cell_metrics that
    ###group the data in df by the cell_name column
    per_cell_metrics = df.groupby('cell_name')[['spend','impressions','population_reached']].mean()
    ##average the spend, impressions, and reach columns
    ##per_cell_metrics = df.groupby('cell_name').mean()[['spend','impressions','population_reached']]
elif test_type == 'YouTube':
    ##create a dataframe called per_cell_metrics that
    ###group the data in df by the study_name column
    ##average the spend and reach columns
    per_cell_metrics = df.groupby('cell_name')[['experiment_cost_usd','treatment_user_count']].mean()
    ##per_cell_metrics = df.groupby('study_name').mean()[['experiment_cost_usd','treatment_user_count']]
elif test_type == 'The Trade Desk':
    per_cell_metrics = df.groupby('cell_name')[['experiment_cost_usd','n_test']].mean()


###create a dataframe with topline metrics for the test
## if the test_type is facebook, the dataframe should have the following columns: metric_name, metric_value
##call the dataframe topline_metrics
##if the test_type is facebook, the dataframe should have the following rows: Cells, Spend (USD), Impressions, Reach
##if the test_type is facebook, the dataframe should have the following values: the number of cells in the test
# which is the number of rows in the per_cell_metrics dataframe rounded
##the spend value is the sum of the spend column in the per_cell_metrics dataframe rounded
##the impressions value is the sum of the impressions column in the per_cell_metrics dataframe rounded
if test_type == 'Facebook':
    topline_metrics = pd.DataFrame({'Metric Name':['Cells','Spend (USD)','Impressions','Reach'],
                                    'Metric Value':[round(per_cell_metrics.shape[0]),
                                                    round(per_cell_metrics['spend'].sum()),
                                                    round(per_cell_metrics['impressions'].sum()),
                                                    round(per_cell_metrics['population_reached'].sum())]})
elif test_type == 'YouTube':
    topline_metrics = pd.DataFrame({'Metric Name':['Cells','Spend (USD)','Reach'],
                                    'Metric Value':[round(per_cell_metrics.shape[0]),
                                                    round(per_cell_metrics['experiment_cost_usd'].sum()),
                                                    round(per_cell_metrics['treatment_user_count'].sum())]})
elif test_type == 'The Trade Desk':
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


if test_type == 'YouTube':
    ##reduce dataframe to only the rows where the value of analysis_date is 'LATEST'
    df = df[df['analysis_day_string'] == 'LATEST']
elif test_type == 'The Trade Desk':
    ##find the max values of the Date column in df for each cell_name
    max_dates = df.groupby('cell_name')['Date'].max()
    ##reduce dataframe to only the rows where the date column is the max value in the date column for each cell_name
    df = df[df['Date'].isin(max_dates)]

## debug print removed


## Reduce to only useful columns
useful_columns = ['analysis_date',
                  'study_name',
                  'treatment_user_count',
                  'control_user_count',
                  'treatment_conversions',
                  'control_conversions',
                  'experiment_cost_usd',
                  'cpis',
                  'conversion_segment',
                  'absolute_lift_confidence_level'
                 ]

metrics_df = df[useful_columns]

## reduce metrics_df to only the rows where the value of conversion_segment is in the list conversion_metrics
## apply the previously-defined `conversion_segment_filter` to `metrics_df`
metrics_df = metrics_df[metrics_df['conversion_segment'].apply(conversion_segment_filter)]


## set seed
np.random.seed(seed = 1234)

alpha_prior = 1e-9
beta_prior = 1e-9


if test_type == 'YouTube':
    ##change the values in the conversion_segment column to be the string between the parentheses in the value
    metrics_df['conversion_segment'] = metrics_df['conversion_segment'].apply(lambda x: x.split('(')[1].split(')')[0])


## create a dataframe to hold the results
## For split tests: each row is one cell, and we compute its conversion rate posterior
results = pd.DataFrame()
inc = 0
for objective in metrics_df['conversion_segment'].unique():
    for cell in metrics_df[(metrics_df['conversion_segment']==objective)]['study_name'].unique():
        sub_df =  metrics_df[(metrics_df['conversion_segment']==objective) & 
                             (metrics_df['study_name']==cell)]
        sub_df = sub_df.reset_index()
        for dt in metrics_df['analysis_date'].unique():
            sub_df_sub = sub_df[(sub_df['analysis_date']== dt)].reset_index()
            # For split tests, use treatment_conversions and treatment_user_count for each cell's conversion rate
            cell_alpha_posterior = alpha_prior + sub_df_sub['treatment_conversions'][0]
            cell_beta_posterior = beta_prior + sub_df_sub['treatment_user_count'][0] - sub_df_sub['treatment_conversions'][0]

            temp_df = pd.DataFrame({'dt': dt,
                                    'cell': cell,
                                    'metric': objective,
                                    'cell_alpha_posterior': cell_alpha_posterior,
                                    'cell_beta_posterior': cell_beta_posterior,
                                    'cpis': sub_df_sub['cpis'][0],
                                    'spend': sub_df_sub['experiment_cost_usd'][0],
                                    'population_test': sub_df_sub['treatment_user_count'][0],
                                    'conf_level': sub_df['absolute_lift_confidence_level'][0],
                                    'conversions': sub_df_sub['treatment_conversions'][0]
                                   }, 
                                    index = [inc])

            results = pd.concat([results,temp_df])
            inc+= 1


if 'win_prob_df' in st.session_state and 'samples_df' in st.session_state:
    win_prob_df = st.session_state['win_prob_df']
    samples_df = st.session_state['samples_df']
else:
    win_prob_df, samples_df = compute_win_probabilities(results, n_sims)
    st.session_state['win_prob_df'] = win_prob_df
    st.session_state['samples_df'] = samples_df


###add subheader that displays topline results
st.subheader('Winning Probability by Cell')
summary_table = win_prob_df[['dt', 'cell', 'metric', 'win_prob', 'cpis']]
##change the name of the column win_prob to Winning Probability
summary_table = summary_table.rename(columns = {'win_prob': 'Winning Probability'})
##change the name of the column cpis to CPiS
summary_table = summary_table.rename(columns = {'cpis': 'CPiS'})
##change the name of the column cell to Cell
summary_table = summary_table.rename(columns = {'cell': 'Cell'})

##create a new table that is the summary table but without the dt column
##call the new table to_view_2
to_view_2 = summary_table.drop(columns = ['dt'])

## format the values in Winning Probability column in to_view_2 to be percentages with one decimal place
to_view_2['Winning Probability'] = to_view_2['Winning Probability'].apply(lambda x: '{:.1%}'.format(x))
## format the values in CPiS column in to_view_2 to be currency with no decimal places
##currency is dollars
to_view_2['CPiS'] = to_view_2['CPiS'].apply(lambda x: '${:,.0f}'.format(x))

## display the df to_view_2 in the app with no index
st.write(to_view_2.set_index('Cell'))





## Skip confidence interval plots for split tests; density plots show the posteriors better
## Placeholder for future metric visualizations
st.subheader('Conversion Rate Distributions by Cell')



## Add density plots
st.subheader('[Density Plots](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')
#### In a column

sns.set()
sns.set_context('talk')
sns.set_style('darkgrid')


grid = sns.FacetGrid(samples_df[['date','cell','metric','conversion_rate_samples']], 
                     row='metric',
                     #row='date',
                     hue='cell' ,height=3.5, aspect=2)

grid.map(sns.kdeplot, 'conversion_rate_samples', shade=True)
#grid.set(xlim=(0, 1))


## Set Titles
grid.set_titles(row_template="{row_name}")

## Add Legend
grid.add_legend(title="Cells")

### Set Axis Labels
grid.set_axis_labels("Conversion Rate", "Density")


## set density number format to include comma separator
current_values = plt.gca().get_yticks()
plt.gca().set_yticklabels(['{:,.0f}'.format(x) for x in current_values])
xx_values = plt.gca().get_xticks()

#change x axis to be percentages
## make it have two decimal place
plt.gca().set_xticklabels(['{:.2%}'.format(x) for x in xx_values])

## add a line to show the zero-line (not applicable for split test conversion rates; omitted)


fig2 = grid.fig
## write to streamlit
st.pyplot(fig2)

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
