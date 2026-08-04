"""Incrementality test workflow."""

from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st
from scipy.stats import beta, norm

from winprob.config import RED
from winprob.llm_summary import build_incrementality_summary_context
from winprob.plotting import (
    apply_dark_axes,
    cache_and_download_figure,
    cache_csv,
    render_incrementality_density_grid,
)
from winprob.ui import render_ai_summary_section


def run_incrementality_app():
    st.header("Incrementality Test (Treatment vs. Control)")


    st.subheader('Test Parameters')
    """
    See [here](https://docs.google.com/spreadsheets/d/1IqLLR7CRkyFwgZaQqst0L3TcA8C24K9h6L_dyUx_sFI/edit?usp=sharing) for an input template with the correct format for Incrementality Test Data.
    """


    ##add a button that allows the user to upload the test data as a csv or an excel file
    ##if the user clicks the button, open up a dialog box that allows the user to browse their computer and select the file
    ##also allow the user to drag and drop the file into the app

    input_file = st.file_uploader('Upload Test Data as a CSV or Excel file:', type=['csv', 'xlsx'])

    #Read in data from the file the user uploaded
    ##if the user uploaded an excel file, read the file into a dataframe called raw
    ##if the user uploaded a csv file, read the file into a dataframe called raw
    ##if the user uploaded a file that is not a csv or an excel file, print 'please upload a csv or an excel file'
    if input_file is None:
        st.stop()
    elif input_file.name.endswith('.xlsx'):
        try:
            raw = pd.read_excel(input_file)
        except Exception as e:
            st.error(f"Could not read Excel file: {e}")
            st.stop()
        if raw.columns[0] != 'cell_name':
            st.error('Incorrect format: the first column must be `cell_name`. See [here](https://docs.google.com/spreadsheets/d/1IqLLR7CRkyFwgZaQqst0L3TcA8C24K9h6L_dyUx_sFI/edit?usp=sharing) for the correct format.')
            st.stop()
    elif input_file.name.endswith('.csv'):
        try:
            raw = pd.read_csv(input_file, header=None)
        except Exception as e:
            st.error(f"Could not read CSV file: {e}")
            st.stop()
    else:
        st.error('Please upload a .csv or .xlsx file.')
        st.stop()


    ##add a slider that allows the user to selet the number of simulations to run
    ##the key for the slider is num_simulations
    ##the default value is 25000
    ##the minimum value is 1000 and the maximum value is 100000
    n_sims = st.slider('Select the number of simulations to run (more simulations will give more stable results, but takes longer):', 1000, 100000, 5000)

    significance_threshold = st.slider(
        'Minimum significance (confidence level) for a cell to be eligible to win:',
        min_value=0.0,
        max_value=1.0,
        value=0.90,
        step=0.05,
        help='Cells with confidence below this threshold are excluded from winning probability. Winning probability is based on lowest simulated CPiS among eligible cells.'
    )

    df = raw.copy()

    df['analysis_date'] = datetime.now().strftime('%Y-%m-%d')


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
    if 'relative_lift' in df.columns:
        df['relative_lift'] = pd.to_numeric(df['relative_lift'], errors='coerce')
    if 'test_conv_rate' in df.columns and 'control_conv_rate' in df.columns:
        df['test_conv_rate'] = pd.to_numeric(df['test_conv_rate'], errors='coerce')
        df['control_conv_rate'] = pd.to_numeric(df['control_conv_rate'], errors='coerce')

    # #create a column called absolutelift_CI that is the absolute lift confidence interval
    # #derive the absolute lift confidence interval from the absolute lift confidence level
    # #get the z score for the absolute lift confidence level
    # #add the z score to the dataframe


    # if absolute_lift_CI_max and min have values, use the following logic to calc absolutelift_CI
    # Ensure columns exist before check
    if 'absolute_lift_CI_max' in df.columns and 'absolute_lift_CI_min' in df.columns \
        and df['absolute_lift_CI_max'].notnull().all() \
        and df['absolute_lift_CI_min'].notnull().all():

        df['absolute_lift_CI_max'] = pd.to_numeric(df['absolute_lift_CI_max'])
        df['absolute_lift_CI_min'] = pd.to_numeric(df['absolute_lift_CI_min'])

        df['absolutelift_CI'] =  (df['absolute_lift_CI_max']-df['absolute_lift_CI_min'])/2
    else:
        df['z_score'] = norm.ppf(df['absolute_lift_confidence_level'])
        ##find the standard error of the absolute lift
        #df['phat'] = (df['treatment_conversions']+df['control_conversions'])/(df['treatment_user_count']+df['control_user_count'])
        #df['se']= df['phat']*(1-df['phat'])/ (df['treatment_user_count']+df['control_user_count'])
        #df['standard_error'] =  (df['se']).sqrt()
        df['standard_error'] = df['absolute_lift']/df['z_score']
        #create the absolute lift confidence interval column based on the standard error and the z score for 90% confidence
        df['absolutelift_CI'] = df['standard_error']*norm.ppf(0.90)
        df['absolutelift_CI'] = df['absolutelift_CI'].abs()



    ### in the df dataframe, if the conversions incremental is 0, change it to equal to 1
    df['absolute_lift'] = df['absolute_lift'].replace(0,1)

    ##add buttons to the app that allows the user to select one or more items the list of available conversion metrics
    ## The conversion metrics are the unique values in the objective_name column in df
    ## The conversion metrics are sorted in alphabetical order
    ## allow the user to select more than one conversion metric
    ## the key for the buttons is conversion_metrics
    ## default is all that none are selected
    conversion_metrics = st.multiselect('Select at least one conversion metric to be analyzed:', sorted(df['conversion_segment'].unique()))

    ##create an empty variable called export_as_pdf
    user_clicked_run = 0

    if st.button('Run Analysis'):
        user_clicked_run = 1
        
    #if conversion_metrics, test_type, and input_file are not empty, allow the user to click a button that says 'Run Analysis'
    ##otherwise, print 'Please select a conversion metric, test vendor, and upload a file'
    ##only run the code below if the user clicks the 'Run Analysis' button
    if conversion_metrics and input_file is not None:
        st.write('Ready to Go!')
        ##continue the code if the user clicks a Run Analysis button and the export_as_pdf variable is empty or if the user clicks the export as pdf button
        if user_clicked_run == 1:
            ## add a line separator to the app
            st.markdown('---')
            ## do not stop the app if the user clicks the export as pdf button
            ## otherwise stop the app
        else:
            st.stop()
    else:
        st.write('Please select at least one conversion metric.')
        ##stop the code from running below to prevent errors from displaying
        st.stop()



    ##write test_name to the app as a subheader
    st.subheader('Test Name')

    ##without the file extension
    test_name = input_file.name.split('.')[0]

    st.write(test_name)

    ## reduce df to only the rows where the value of conversion_segment is in the list conversion_metrics
    ## write a function that returns True if the value of conversion_segment is in the list conversion_metrics
    def conversion_segment_filter(x):
        if x in conversion_metrics:
            return True
        else:
            return False
    ## apply the conversion_segment_filter function to the conversion_segment column in df
    df = df[df['conversion_segment'].apply(conversion_segment_filter)]

    st.subheader('Media Metrics')

    per_cell_metrics = df.groupby('cell_name')[['experiment_cost_usd', 'n_test']].mean()
    topline_metrics = pd.DataFrame({
        'Metric Name': ['Cells', 'Spend (USD)', 'Reach'],
        'Metric Value': [
            round(per_cell_metrics.shape[0]),
            round(per_cell_metrics['experiment_cost_usd'].sum()),
            round(per_cell_metrics['n_test'].sum())
        ]
    })

    hide_table_row_index = """
                <style>
                thead tr th:first-child {display:none}
                tbody th {display:none}
                </style>
                """
    st.markdown(hide_table_row_index, unsafe_allow_html=True)
    topline_metrics['Metric Value'] = topline_metrics['Metric Value'].apply(lambda x: '{:,}'.format(x))
    topline_metrics['Metric Value'][1] = '$' + topline_metrics['Metric Value'][1]
    st.table(topline_metrics)

    ##print the number of rows in the dataframe
    print(df.shape[0])


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
    if 'relative_lift' in df.columns:
        useful_columns.append('relative_lift')

    metrics_df = df[useful_columns]

    ## reduce metrics_df to only the rows where the value of conversion_segment is in the list conversion_metrics
    ## write a function that returns True if the value of conversion_segment is in the list conversion_metrics
    def conversion_segment_filter(x):
        if x in conversion_metrics:
            return True
        else:
            return False

    ## apply the conversion_segment_filter function to the conversion_segment column in metrics_df
    metrics_df = metrics_df[metrics_df['conversion_segment'].apply(conversion_segment_filter)]


    ## set seed
    np.random.seed(seed = 1234)

    alpha_prior = 1
    beta_prior = 1


    ## create a dataframe to hold the results
    results = pd.DataFrame()
    inc = 0
    for objective in metrics_df['conversion_segment'].unique():
        #print(objective)
        for cell in metrics_df[(metrics_df['conversion_segment']==objective)]['study_name'].unique():
            sub_df =  metrics_df[(metrics_df['conversion_segment']==objective) & 
                                (metrics_df['study_name']==cell)]
            sub_df = sub_df.reset_index()
            for dt in metrics_df['analysis_date'].unique():
                sub_df_sub = sub_df[(sub_df['analysis_date']== dt)].reset_index()
                test_alpha_posterior = alpha_prior + sub_df_sub['treatment_conversions'][0]
                #test_beta_posterior = beta_prior + sub_df['population.test'][0] - test_alpha_posterior
                test_beta_posterior = beta_prior + sub_df_sub['treatment_user_count'][0] - sub_df_sub['treatment_conversions'][0]

                ctl_alpha_posterior = alpha_prior + sub_df_sub['control_conversions'][0]
                #ctl_beta_posterior = beta_prior + sub_df['population.control'][0] - ctl_alpha_posterior
                ctl_beta_posterior = beta_prior + sub_df_sub['control_user_count'][0] - sub_df_sub['control_conversions'][0]
                
                
                # pdiff = test_alpha_posterior/(test_alpha_posterior+test_beta_posterior) - ctl_alpha_posterior/(ctl_alpha_posterior+ctl_beta_posterior)
                
                test_rate = test_alpha_posterior/(test_alpha_posterior+test_beta_posterior)
                ctl_rate  = ctl_alpha_posterior/(ctl_alpha_posterior+ctl_beta_posterior)
                cvr_lift = test_rate - ctl_rate
                pdiff = cvr_lift * sub_df_sub['treatment_user_count'][0]
                if 'relative_lift' in sub_df_sub.columns and pd.notnull(sub_df_sub['relative_lift'][0]):
                    relative_cvr_lift = sub_df_sub['relative_lift'][0]
                elif ctl_rate > 0:
                    relative_cvr_lift = cvr_lift / ctl_rate
                else:
                    relative_cvr_lift = np.nan
        
                temp_df = pd.DataFrame({'dt': dt,
                                        'cell': cell,
                                        #'metric': metric[:-1],
                                        'metric': objective,
                                        'test_alpha_posterior': test_alpha_posterior ,
                                        'test_beta_posterior': test_beta_posterior , 
                                        'ctl_alpha_posterior': ctl_alpha_posterior ,
                                        'ctl_beta_posterior': ctl_beta_posterior ,
                                        'cpis': sub_df_sub['cpis'][0],
                                        'spend': sub_df_sub['experiment_cost_usd'][0],
                                        'population_test':sub_df_sub['treatment_user_count'][0],
                                        'conf_level': sub_df['absolute_lift_confidence_level'][0],
                                        'cvr_lift': cvr_lift,
                                        'relative_cvr_lift': relative_cvr_lift,
                                        'incremental_conversions': pdiff,
                                        'pdiff': pdiff
                                    }, 
                                        index = [inc])

                results = pd.concat([results,temp_df])
                inc+= 1

    results['significance_eligible'] = results['conf_level'] >= significance_threshold

    per_cell_display = results[[
        'cell', 'metric', 'cvr_lift', 'relative_cvr_lift',
        'incremental_conversions', 'cpis', 'conf_level', 'significance_eligible'
    ]].copy()
    per_cell_display = per_cell_display.rename(columns={
        'cell': 'Cell',
        'metric': 'Metric',
        'cvr_lift': 'Absolute CVR Lift',
        'relative_cvr_lift': 'Relative CVR Lift',
        'incremental_conversions': 'Incremental Conversions',
        'cpis': 'CPiS',
        'conf_level': 'Significance',
        'significance_eligible': 'Eligible to Win'
    })

    per_cell_view = per_cell_display.copy()
    per_cell_view['Absolute CVR Lift'] = per_cell_view['Absolute CVR Lift'].apply(lambda x: f'{x:.4%}')
    per_cell_view['Relative CVR Lift'] = per_cell_view['Relative CVR Lift'].apply(
        lambda x: f'{x:.1%}' if pd.notnull(x) else 'N/A'
    )
    per_cell_view['Incremental Conversions'] = per_cell_view['Incremental Conversions'].apply(
        lambda x: f'{x:,.0f}'
    )
    per_cell_view['CPiS'] = per_cell_view['CPiS'].apply(lambda x: f'${x:,.2f}')
    per_cell_view['Significance'] = per_cell_view['Significance'].apply(lambda x: f'{x:.1%}')
    per_cell_view['Eligible to Win'] = per_cell_view['Eligible to Win'].map({True: 'Yes', False: 'No'})

    st.subheader('Per-Cell Performance Metrics')
    st.caption(
        'Absolute CVR lift and incremental conversions use Bayesian posterior point estimates. '
        f'Cells must meet the {significance_threshold:.0%} significance threshold to be eligible for winning probability.'
    )
    st.write(per_cell_view.set_index('Cell'))


    win_prob_df = pd.DataFrame()
    samples_df = pd.DataFrame()

    for dt in results['dt'].unique():
        print(dt)
        for metric in results['metric'].unique():
            #print(metric)
            sub_results = results[(results['dt']==dt) & 
                                (results['metric']==metric)].reset_index()
            sims = pd.DataFrame()
            wins = np.zeros(len(sub_results['cell'].unique(), ))
            for i in range(len(sub_results['cell'].unique())):
                conf_level = sub_results['conf_level'][i]
                spend = sub_results['spend'][i]
                if conf_level > 0.0:
                    test = beta(sub_results['test_alpha_posterior'][i], sub_results['test_beta_posterior'][i]).rvs(n_sims)
                    ctl = beta(sub_results['ctl_alpha_posterior'][i], sub_results['ctl_beta_posterior'][i]).rvs(n_sims)
                else:
                    test = np.zeros(n_sims)
                    ctl = np.zeros(n_sims)
                sub_samples = pd.DataFrame({'analysis_date': dt, 
                                            'cell': sub_results['cell'][i],
                                        'metric': metric, 
                                            'spend': spend,
                                            'population_test': sub_results['population_test'][i],
                                            'test_samples': test, 
                                            'control_samples': ctl})
                samples_df = pd.concat([samples_df,sub_samples])

                incrementals = (test - ctl) * sub_results['population_test'][i]
                with np.errstate(divide='ignore', invalid='ignore'):
                    cpis_samples = spend / incrementals
                if conf_level < significance_threshold:
                    cpis_samples = np.full(n_sims, np.inf)
                else:
                    cpis_samples = np.where(incrementals > 0, cpis_samples, np.inf)

                sims[i] = cpis_samples
                wins[i] = 0
                
            for i in range(n_sims):
                row = sims.loc[i, :].to_numpy(dtype=float)
                eligible = np.isfinite(row)
                if eligible.any():
                    winner_idx = np.where(eligible)[0][np.argmin(row[eligible])]
                    wins[winner_idx] += 1
            sub_results['win_prob'] = [(x + 0.0)/n_sims for x in wins]
            win_prob_df = pd.concat([win_prob_df,sub_results])


    samples_df['cvr_lift_samples'] = samples_df['test_samples'] - samples_df['control_samples']
    with np.errstate(divide='ignore', invalid='ignore'):
        samples_df['relative_cvr_lift_samples'] = np.where(
            samples_df['control_samples'] > 0,
            samples_df['cvr_lift_samples'] / samples_df['control_samples'],
            np.nan
        )
    samples_df['incremental_conversion_samples'] = (
        samples_df['cvr_lift_samples'] * samples_df['population_test']
    )
    samples_df['cpis_samples'] = samples_df['spend'] / samples_df['incremental_conversion_samples']


    ###add subheader that displays topline results
    st.subheader('[Winning Probability](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) and [CPiS](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) by Cell')
    st.caption(
        'Winning probability is the share of simulations where a cell has the lowest CPiS among cells '
        f'that meet the {significance_threshold:.0%} significance threshold and produce positive incremental conversions.'
    )
    summary_table = win_prob_df[[
        'dt', 'cell', 'metric', 'win_prob', 'cvr_lift', 'incremental_conversions',
        'cpis', 'conf_level', 'significance_eligible'
    ]]
    summary_table = summary_table.rename(columns={
        'win_prob': 'Winning Probability',
        'cpis': 'CPiS',
        'cell': 'Cell',
        'cvr_lift': 'Absolute CVR Lift',
        'incremental_conversions': 'Incremental Conversions',
        'conf_level': 'Significance',
        'significance_eligible': 'Eligible to Win'
    })

    ##create a new table that is the summary table but without the dt column
    ##call the new table to_view_2
    to_view_2 = summary_table.drop(columns = ['dt'])

    to_view_2['Winning Probability'] = to_view_2['Winning Probability'].apply(lambda x: '{:.1%}'.format(x))
    to_view_2['Absolute CVR Lift'] = to_view_2['Absolute CVR Lift'].apply(lambda x: '{:.4%}'.format(x))
    to_view_2['Incremental Conversions'] = to_view_2['Incremental Conversions'].apply(lambda x: '{:,.0f}'.format(x))
    to_view_2['CPiS'] = to_view_2['CPiS'].apply(lambda x: '${:,.2f}'.format(x))
    to_view_2['Significance'] = to_view_2['Significance'].apply(lambda x: '{:.1%}'.format(x))
    to_view_2['Eligible to Win'] = to_view_2['Eligible to Win'].map({True: 'Yes', False: 'No'})

    ## display the df to_view_2 in the app with no index
    st.write(to_view_2.set_index('Cell'))

    # ---- CSV outputs download----
    if 'summary_table' in locals() and isinstance(summary_table, pd.DataFrame):
        cache_csv(summary_table, "incrementality_results_csv")

        st.download_button(
            "Download Winning Probability Summary CSV",
            data=st.session_state["incrementality_results_csv"],
            file_name="incrementality_winning_prob.csv",
            mime="text/csv"
        )


    confidence_interval_explanation = """
    Confidence Intervals are a way to measure the uncertainty of a statistic.
    """

    ###add subheader for the confidence intervals
    st.subheader('[Confidence Intervals](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')
    ##add an expander to the app
    ##the expander will display the text in the variable confidence_interval_explanation
    ##expander = st.expander("What is a Confidence Interval?")

    #plot confidence intervals 
    sns.set_style('darkgrid')


    # CIs for incremental conversions/absolute lift
    for obj in df['conversion_segment'].unique():
        sub_df = df[(df['conversion_segment'])==obj]
        # Set sns plot style back to 'poster' to make bars wide on plot
        sns.set_context("poster")

        fig, ax = plt.subplots(figsize=(10, 4))

        ax.errorbar(
            x=sub_df['study_name'],
            y=sub_df['absolute_lift'],
            yerr=sub_df['absolutelift_CI'],
            fmt='o',
            ecolor='green',
            capsize=5,
            capthick=2
        )

        ax.axhline(0, color=RED, linestyle='--', linewidth=1.5)

        ax.set_title(obj, fontsize=15)
        ax.set_ylabel("Incremental Conversions", fontsize=15)
        ax.set_xlabel("")

        ax.tick_params(axis='x', labelsize=15, rotation=45)
        ax.tick_params(axis='y', labelsize=15)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda x, _: f"{int(x):,}")
        )

        ax.legend(
            ['No lift', '90% Confidence Interval'],
            loc='upper center',
            fontsize=15,
            bbox_to_anchor=(0.5, 1.35),
            ncol=2
        )

        apply_dark_axes(ax)
        plt.title(f"{obj} - CI/Error Bar", fontsize=14)
        st.pyplot(fig)


        # ---- CI plot download ----
        cache_and_download_figure(
                fig,
                key=f"Incr_CI_{obj}",
                filename_prefix=f"Incrementality_CI_{obj}"
            )
## og
        # fig, ax = plt.subplots(figsize=(10, 4))
        # ax.tick_params(axis='x', rotation=45, labelsize=12, pad=-10)
        # ax.tick_params(axis='y',labelsize=13)

        # plt.errorbar(x=np.array(sub_df['study_name']), 
        #             y=np.array(sub_df['absolute_lift']), 
        #             #  yerr=np.array(list(zip(sub_df['absolutelift']-sub_df['absolutelift_CImin'],sub_df['absolutelift_CImax']-sub_df['absolute_lift']))).T,
        #             yerr=np.array(sub_df['absolutelift_CI']),
        #             fmt='o', ecolor='g', capthick=2)

        # # Set title & labels
        # ##plt.title('Incremental Buyers w/ 90% Confidence Intervals {y}',fontsize=15)
        # plt.title(obj,fontsize=15)
        # ax.set_ylabel("Incremental Conversions",fontsize=12)
        # ax.set_xlabel('', fontsize=12)


        # # Line to define zero on the y-axis
        # ## line should apply to all plots in fig
        # ## line should be red and dashed
        # ## line should be at the y value of 0
        # ax.axhline(y=0, color='r', linestyle='--')
    
        
        # ## set density number format to include comma separator
        # current_values = plt.gca().get_yticks()
        # plt.gca().set_yticklabels(['{:,.0f}'.format(x) for x in current_values])

        # ## create a legend that is outside of the plot
        # ## the legend should be above the plot
        # ## the legend should denote the confidence interval as "90% Confidence Interval"
        # ## the legend should should say "90% Confidence Interval" for the error bars
        # ## the legend should say "No lift" for the red line
        # ## the legend should be above the entire plot and not just the plot itself
        # ## the legend should be outside of the plot and not inside the plot
        # ## the legend should be to the right of the plot and not to the left of the plot
        # plt.legend(['No lift','90% Confidence Interval'],bbox_to_anchor = (0.5,1.5),loc='upper center', ncol=2)


        # plt.show()
        # st.write(fig)

    ## Add density plots
    st.subheader('[Density Plots](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')

    density_plot_df = samples_df[[
        'analysis_date', 'cell', 'metric',
        'cvr_lift_samples', 'relative_cvr_lift_samples', 'incremental_conversion_samples'
    ]].copy()
    density_plot_df = density_plot_df.dropna(subset=['cvr_lift_samples'])

    st.markdown('**Absolute CVR Lift**')
    absolute_cvr_lift_fig = render_incrementality_density_grid(
        density_plot_df[['analysis_date', 'cell', 'metric', 'cvr_lift_samples']],
        'cvr_lift_samples',
        'Absolute CVR Lift',
        x_tick_format='percent'
    )
    st.pyplot(absolute_cvr_lift_fig)
    cache_and_download_figure(
        absolute_cvr_lift_fig,
        key="Incr_Absolute_CVR_Lift_Density",
        filename_prefix="Incrementality_Absolute_CVR_Lift_Density"
    )

    relative_density_df = density_plot_df.dropna(subset=['relative_cvr_lift_samples'])
    st.markdown('**Relative CVR Lift**')
    relative_cvr_lift_fig = render_incrementality_density_grid(
        relative_density_df[['analysis_date', 'cell', 'metric', 'relative_cvr_lift_samples']],
        'relative_cvr_lift_samples',
        'Relative CVR Lift',
        x_tick_format='percent'
    )
    st.pyplot(relative_cvr_lift_fig)
    cache_and_download_figure(
        relative_cvr_lift_fig,
        key="Incr_Relative_CVR_Lift_Density",
        filename_prefix="Incrementality_Relative_CVR_Lift_Density"
    )

    st.markdown('**Incremental Conversions**')
    incremental_fig = render_incrementality_density_grid(
        density_plot_df[['analysis_date', 'cell', 'metric', 'incremental_conversion_samples']],
        'incremental_conversion_samples',
        'Incremental Conversions',
        x_tick_format='count'
    )
    st.pyplot(incremental_fig)
    cache_and_download_figure(
        incremental_fig,
        key="Incr_Conversions_Density",
        filename_prefix="Incrementality_Incremental_Conversions_Density"
    )

    summary_context = build_incrementality_summary_context(
        test_name=test_name,
        significance_threshold=significance_threshold,
        results_df=results,
        win_prob_df=win_prob_df,
        samples_df=samples_df,
        ci_df=df,
    )
    render_ai_summary_section(summary_context, session_namespace="incrementality")