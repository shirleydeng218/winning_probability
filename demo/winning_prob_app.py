
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from io import BytesIO
import seaborn as sns
from scipy.stats import beta, norm
from datetime import datetime


# =============================
# Setting, Formatting, & Config
# =============================

# App config & formatting
st.set_page_config(
    page_title="Winning Probability App",
    page_icon="👑",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Header with logos
logo_col1, logo_col2, logo_col3 = st.columns([1, 3, 1])

with logo_col1:
    st.image(
        "assets/disney.svg",
        width=120
    )

with logo_col2:
    st.markdown(
        "<h2 style='text-align: center; color: #B8F2E6;'>Marketing Analytics</h2>",
        unsafe_allow_html=True
    )

with logo_col3:
    st.image(
        "assets/hulu.png",
        width=120
    )

st.markdown("---")

# formatting designs
GREEN = "#7ED957"
NAVY = "#0D243B"
GRID = "#2F5175"
TEXT = "#E6F2F0"
LINE = "#E4E1E1C1"
RED = "#F87171"

plt.style.use("dark_background")

sns.set_theme(
    style="darkgrid",
    rc={
        "axes.facecolor": NAVY,
        "figure.facecolor": NAVY,
        "grid.color": GRID,
        "axes.edgecolor": GRID,
        "axes.labelcolor": TEXT,
        "xtick.color": LINE,
        "ytick.color": LINE,
        "text.color": TEXT,
        "legend.frameon": False,
    }
)

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

        buf_pdf = BytesIO()
        fig.savefig(buf_pdf, format="pdf", bbox_inches="tight")
        buf_pdf.seek(0)

        st.session_state[key] = {
            "png": buf_png.getvalue(),
            "pdf": buf_pdf.getvalue()
        }

    st.download_button(
        f"Download {key} PNG",
        data=st.session_state[key]["png"],
        file_name=f"{filename_prefix}.png",
        mime="image/png"
    )

    st.download_button(
        f"Download {key} PDF",
        data=st.session_state[key]["pdf"],
        file_name=f"{filename_prefix}.pdf",
        mime="application/pdf"
    )


def cache_csv(df, key):
    if key not in st.session_state:
        st.session_state[key] = df.to_csv(index=False).encode("utf-8")



# =============================
# Incrementality App
# =============================
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
        raw = pd.read_excel(input_file)
        if raw.columns[0] != 'cell_name':
            st.write('INCORRECT FORMAT: Please upload a file in the correct format. See [here](https://google.com) for details on getting the data in the correct format.')
            st.stop()
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

    ##write the topline metrics to the app as a subheader
    st.subheader('Media Metrics')

    ##create a dataframe called per_cell_metrics
    per_cell_metrics = df.groupby('cell_name')[['experiment_cost_usd','n_test']].mean()


    ###create a dataframe with topline metrics for the test
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
                
                
                pdiff = test_alpha_posterior/(test_alpha_posterior+test_beta_posterior) - ctl_alpha_posterior/(ctl_alpha_posterior+ctl_beta_posterior)

        
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
                                        'pdiff': pdiff
                                    }, 
                                        index = [inc])

                results = pd.concat([results,temp_df])
                inc+= 1


    win_prob_df = pd.DataFrame()
    samples_df = pd.DataFrame()

    for dt in results['dt'].unique():
        print(dt)
        for metric in results['metric'].unique():
            #print(metric)
            sub_results = results[(results['dt']==dt) & 
                                (results['metric']==metric)].reset_index()
            sims = pd.DataFrame()
            #sims2 = pd.DataFrame()
            wins = np.zeros(len(sub_results['cell'].unique(), ))
            #wins2 = np.zeros(len(sub_results['cell'].unique(), ))
            for i in range(len(sub_results['cell'].unique())):
                if sub_results['conf_level'][i] > 0.0:
                    test = beta(sub_results['test_alpha_posterior'][i], sub_results['test_beta_posterior'][i]).rvs(n_sims)
                    ctl = beta(sub_results['ctl_alpha_posterior'][i], sub_results['ctl_beta_posterior'][i]).rvs(n_sims)
                else:
                    test = np.zeros(n_sims)
                    ctl = np.zeros(n_sims)
                sub_samples = pd.DataFrame({'analysis_date': dt, 
                                            'cell': sub_results['cell'][i],
                                        'metric': metric, 
                                            'spend': sub_results['spend'][i],
                                            'population_test': sub_results['population_test'][i],
                                            'test_samples': test, 
                                            'control_samples': ctl})
                samples_df = pd.concat([samples_df,sub_samples])
                sims[i] = test - ctl
                #sims2[i] = sims[i] * sub_results['population_test'][i]
                wins[i] = 0
                #wins2[i] = 0
                
            for i in range(n_sims):
                wins[np.argmax(sims.loc[i,:])] += 1
                #wins2[np.argmax(sims2.loc[i,:])] += 1
            sub_results['win_prob'] = [(x + 0.0)/n_sims for x in wins]
            #sub_results['win_prob2'] = [(x + 0.0)/n_sims for x in wins2]
            win_prob_df = pd.concat([win_prob_df,sub_results])


    samples_df['lift_samples'] = samples_df['test_samples'] -samples_df['control_samples']
    samples_df['cpis_samples'] = samples_df['spend']/(samples_df['population_test'] * samples_df['lift_samples'] )


    ###add subheader that displays topline results
    ## include a link for the word "winning probability" that links to the bottom of the page where "Explanation of Winning Probability" is displayed
    ## include a link for the word "CPiS" that links to the bottom of the page where "Explanation of CPiS" is displayed
    st.subheader('[Winning Probability](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) and [CPiS](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) by Cell')
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

    sns.set_context('talk')
    sns.set_style('darkgrid')

    grid = sns.FacetGrid(
        samples_df[['analysis_date','cell','metric','lift_samples']], 
        row='metric',
        hue='cell',
        height=3.5,
        aspect=2
    )

    grid.map(sns.kdeplot, 'lift_samples', shade=True)

    # Titles, labels, and legend
    grid.set_titles(row_template="{row_name}")
    grid.set_axis_labels("Absolute Lift", "Density")
    # grid.add_legend(title="Cells", fontsize=12)

    # Apply dark theme to each subplot
    for ax in grid.axes.flat:
        # Add vertical line at x=0
        # ax.axvline(x=0, color='r', linestyle='--', label='_nolegend_')

        apply_dark_axes(ax, zero_line=True)  

        # Optional: format y-ticks nicely
        ax.set_yticklabels(['{:,.0f}'.format(x) for x in ax.get_yticks()])
        # Optional: format x-ticks as percentages
        ax.set_xticklabels(['{:.2%}'.format(x) for x in ax.get_xticks()])

        leg = ax.legend(title="Cells", loc='upper left', bbox_to_anchor=(1.02, 1))
        for text in leg.get_texts():
            text.set_color("white")   # change legend text color
        leg.get_title().set_color("white")  # change legend title color

    fig2 = grid.fig
    st.pyplot(fig2)



    # ---- Density plot download----
    cache_and_download_figure(
        fig,
        key=f"Incr_Density_{obj}",
        filename_prefix=f"Incrementality_Density_{obj}"
    )



# ===============================
# Split Test App
# ===============================
def run_split_test_app():
    st.header("Split Test (A/B/C, no control)")

    # Functions
    def compute_win_probabilities(
        results,
        n_sims,
        compare_on='conversion_rate',
        seed=1234,
        rope_eps=1e-4,          # ~1 basis point CVR
        alpha_prior,
        beta_prior
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
                    'analysis_date': dt,
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


    st.subheader('Test Parameters')
    """
    See [here](https://docs.google.com/spreadsheets/d/1XCZSbQNNYVPRl7AEICgsLKCGi-Re_Owk/edit?gid=1708648830#gid=1708648830) for an input template with the correct format for Split Test Data.
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
    max_dates = df.groupby('cell_name')['analysis_date'].max()
    df = df[df['analysis_date'].isin(max_dates)]

    
    st.markdown('---')

    ##write test_name to the app as a subheader
    st.subheader('Test Name')
    ##without the file extension
    test_name = input_file.name.split('.')[0]
    st.write(test_name)


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


    win_prob_df, samples_df = compute_win_probabilities(results, n_sims, compare_on=compare_on, alpha_prior=alpha_prior, beta_prior=beta_prior)
    freq_df = add_frequentist_stats(win_prob_df, compare_on=compare_on)
    win_prob_df = win_prob_df.merge(freq_df, on=['dt', 'cell', 'metric'], how='left')


# ===== display topline metrics =====#
    ##write the topline metrics to the app as a subheader
    st.subheader('Media Metrics')
    ##create a dataframe called per_cell_metrics
    per_cell_metrics = df.groupby('cell_name')[['experiment_cost_usd','n_test']].mean()

    ###create a dataframe with topline metrics for the test
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

# ===== display summary metrics =====#
    # Display summary table
    st.subheader('[Winning Probability Summary](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit) ')
    summary_table = win_prob_df[['cell', 'metric', 'win_prob', 'cps', 'users', 'impressions', 'lift_vs_zero', 'ci_low', 'ci_high', 'p_value']]
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
    ci_key = f"Split_CI_{metric}_{compare_on}"
    cache_and_download_figure(
        fig,
        key=ci_key,
        filename_prefix=f"Split_CI_{metric}_{compare_on}"
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
            s = samples_df[(samples_df['analysis_date'] == dt) & 
                        (samples_df['metric'] == metric) & 
                        (samples_df['cell'] == cell)]['metric_samples'].to_numpy()

            # If single value (absolute metrics), add small jitter for KDE plotting
            if s.size <= 1:
                s = np.repeat(s, n_sims) if s.size == 1 else np.full(n_sims, 0)
                s = s + np.random.normal(0, 0.01 * max(s.max(), 1), size=n_sims)

            density_rows.append(pd.DataFrame({
                'analysis_date': dt,
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

            if compare_on == 'conversion_rate':
                ax.xaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
            
            ax.legend(title='Cells')
            plt.title(f"{metric} - Density Plot", fontsize=15)
            
            apply_dark_axes(ax, zero_line=True)
            leg = ax.legend(title="Cells", loc='upper left', bbox_to_anchor=(1.02, 1))
            for text in leg.get_texts():
                text.set_color("white")   # change legend text color
            leg.get_title().set_color("white")  # change legend title color
            
            # Optional: format y-ticks nicely
            ax.set_yticklabels(['{:,.0f}'.format(x) for x in ax.get_yticks()])
            # Optional: format x-ticks as percentages
            # ax.set_xticklabels(['{:.2%}'.format(x) for x in ax.get_xticks()])

            st.pyplot(fig)
    else:
        st.write('No samples available to plot density for the selected metric.')

    # ---- cache density figure ----
    density_key = f"Split_Density_{metric}_{compare_on}"
    cache_and_download_figure(
        fig,
        key=density_key,
        filename_prefix=f"Split_Density_{metric}_{compare_on}"
    )



# ------------------------
# Streamlit App Flow Below:
# ------------------------


#Set Title
st.title("WinProb: Media Test Evaluator")


"""
This application evaluates media test performance for Disney+ and Hulu by estimating the probability that each test cell is the top performer (winning probability). It supports both *Incrementality tests* (with a control group) and *Split tests* (e.g., A/B/C tests without a control group) conducted with media partners.

Results are generated using Hulu’s proprietary Winning Probability framework, which incorporates statistical uncertainty to provide a more reliable view of relative performance than traditional significance testing.

For additional details, please refer to [the App Documentation](https://docs.google.com/document/d/1XgL30F5GybUdpCsJemZ0kCmOeFwRZDxizqZFM9dJpu8/edit?tab=t.0). For questions or support, please contact Max Wilson or Shirley Deng on the BLADE team at maxim.wilson@disney.com
 or shirley.deng@disney.com.
"""

test_type = st.radio(
    "Please select a test type:",
    [
        "Incrementality test (Treatment vs Control)",
        "Split test (A/B/C without control)"
    ],
    index=None
)

if test_type is None:
    st.info("👆 Select a test type to continue.")
    st.stop()

st.markdown("---")

if test_type == "Incrementality test (Treatment vs Control)":
    run_incrementality_app()

elif test_type == "Split test (A/B/C without control)":
    run_split_test_app()