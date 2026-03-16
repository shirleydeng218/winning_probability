#Functions
def parse_and_standardize(vendor, df, conversion_metrics):
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