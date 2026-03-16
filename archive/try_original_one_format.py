#Import packages
import math
import os
import matplotlib
from collections import namedtuple
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from scipy.stats import beta
from scipy.stats import norm
import seaborn as sns
from datetime import datetime
import base64


#Set Title
st.title('Winning Probability App for Evaluating Incremental Media Tests')

"""
This app calculates the winning probability of cells in incrementality tests (with control) we run with our media vendors.
This methodology is based on Hulu's proprietary winning probability framework.
See [here](https://docs.google.com/document/d/1XgL30F5GybUdpCsJemZ0kCmOeFwRZDxizqZFM9dJpu8/edit?tab=t.0) for App Documentation, or reach out to Max Wilson or Shirley Deng on the BLADE team at maxim.wilson@disney.com or shirley.deng@disney.com for more information.
"""


st.subheader('Test Parameters')
"""
See [here](https://docs.google.com/spreadsheets/d/1XCZSbQNNYVPRl7AEICgsLKCGi-Re_Owk/edit?gid=1708648830#gid=1708648830) for an input template with the correct format.
"""


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
# df['z_score'] = norm.ppf(df['absolute_lift_confidence_level'])

# ##find the standard error of the absolute lift
# #df['phat'] = (df['treatment_conversions']+df['control_conversions'])/(df['treatment_user_count']+df['control_user_count'])
# #df['se']= df['phat']*(1-df['phat'])/ (df['treatment_user_count']+df['control_user_count'])
# #df['standard_error'] =  (df['se']).sqrt()
# df['standard_error'] = df['absolute_lift']/df['z_score']
# #create the absolute lift confidence interval column based on the standard error and the z score for 90% confidence
# df['absolutelift_CI'] = df['standard_error']*norm.ppf(0.90)
# df['absolutelift_CI'] = df['absolutelift_CI'].abs()

df['absolute_lift_CI_max'] = pd.to_numeric(df['absolute_lift_CI_max'])
df['absolute_lift_CI_min'] = pd.to_numeric(df['absolute_lift_CI_min'])

df['absolutelift_CI'] =  (df['absolute_lift_CI_max']-df['absolute_lift_CI_min'])/2
print(df['absolutelift_CI'])


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



##find the max values of the Date column in df for each cell_name
max_dates = df.groupby('cell_name')['Date'].max()
##reduce dataframe to only the rows where the date column is the max value in the date column for each cell_name
df = df[df['Date'].isin(max_dates)]

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
            sub_samples = pd.DataFrame({'date': dt, 
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



# CIs for incremental conversions/absolute lift
for obj in df['conversion_segment'].unique():
    sub_df = df[(df['conversion_segment'])==obj]
    # Set sns plot style back to 'poster' to make bars wide on plot
    sns.set_context("poster")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.tick_params(axis='x', rotation=45, labelsize=12, pad=-10)
    ax.tick_params(axis='y',labelsize=13)

    plt.errorbar(x=np.array(sub_df['study_name']), 
                 y=np.array(sub_df['absolute_lift']), 
                #  yerr=np.array(list(zip(sub_df['absolutelift']-sub_df['absolutelift_CImin'],sub_df['absolutelift_CImax']-sub_df['absolute_lift']))).T,
                 yerr=np.array(sub_df['absolutelift_CI']),
                 fmt='o', ecolor='g', capthick=2)

    # Set title & labels
    ##plt.title('Incremental Buyers w/ 90% Confidence Intervals {y}',fontsize=15)
    plt.title(obj,fontsize=15)
    ax.set_ylabel("Incremental Conversions",fontsize=12)
    ax.set_xlabel('', fontsize=12)


    # Line to define zero on the y-axis
    ## line should apply to all plots in fig
    ## line should be red and dashed
    ## line should be at the y value of 0
    ax.axhline(y=0, color='r', linestyle='--')
   
    
    ## set density number format to include comma separator
    current_values = plt.gca().get_yticks()
    plt.gca().set_yticklabels(['{:,.0f}'.format(x) for x in current_values])

    ## create a legend that is outside of the plot
    ## the legend should be above the plot
    ## the legend should denote the confidence interval as "90% Confidence Interval"
    ## the legend should should say "90% Confidence Interval" for the error bars
    ## the legend should say "No lift" for the red line
    ## the legend should be above the entire plot and not just the plot itself
    ## the legend should be outside of the plot and not inside the plot
    ## the legend should be to the right of the plot and not to the left of the plot
    plt.legend(['No lift','90% Confidence Interval'],bbox_to_anchor = (0.5,1.5),loc='upper center', ncol=2)




    plt.show()
    st.write(fig)



## Add density plots
st.subheader('[Density Plots](https://docs.google.com/presentation/d/1pvENyzIFNAN6yQ3bEEPDUD4TyLhz00GJ_CZcX0WhCGA/edit)')
#### In a column

sns.set()
sns.set_context('talk')
sns.set_style('darkgrid')


grid = sns.FacetGrid(samples_df[['date','cell','metric','lift_samples']], 
                     row='metric',
                     #row='date',
                     hue='cell' ,height=3.5, aspect=2)

grid.map(sns.kdeplot, 'lift_samples', shade=True)
#grid.set(xlim=(-100000, 100000))


## Set Titles
grid.set_titles(row_template="{row_name}")

## Add Legend
grid.add_legend(title="Cells")

### Set Axis Labels
grid.set_axis_labels("Absolute Lift", "Density")


## set density number format to include comma separator
current_values = plt.gca().get_yticks()
plt.gca().set_yticklabels(['{:,.0f}'.format(x) for x in current_values])
xx_values = plt.gca().get_xticks()
##plt.gca().set_xticklabels(['{:%.0f%%}'.format(x) for x in xx_values])



#change x axis to be percentages
## make it have two decimal place
plt.gca().set_xticklabels(['{:.2%}'.format(x) for x in xx_values])

## add a red line to show the zero lift
## line should apply to all plots in fig
## line should be red and dashed
## line should be at the x value of 0
grid.map(plt.axvline, x=0, color='r', linestyle='--')


fig2 = grid.fig
## write to streamlit
st.pyplot(fig2)

