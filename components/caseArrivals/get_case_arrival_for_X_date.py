import holidays
import pandas as pd
from prophet import Prophet

"""
Function to reformat case arrival file and recalculate case arrival forecast 

-Should eventually collect case arrivals from database? No updates after april 2024 
"""

def getForcast(date):
    print("Updating times series forecast")
    df = pd.read_csv('../caseArrival/CaseArrivalCountsApril.csv')
    df['day'] = pd.to_datetime(df['day'], utc=True)
    date = pd.to_datetime(date, utc=True)

    df = df[df['day'] < date]
    df['day'] = df['day'].dt.date
    df['day'] = df['day'] + pd.Timedelta(days=1)
    df.rename(columns={'day': 'ds', 'event_count': 'y'}, inplace=True)

    Q1 = df['y'].quantile(0.05)
    Q3 = df['y'].quantile(0.95)
    IQR = Q3 - Q1

    lower_bound = max(df['y'].quantile(0.05), Q1 - 1.5 * IQR)
    upper_bound = Q3 + 1.5 * IQR

    df_cleaned = df[(df['y'] >= lower_bound) & (df['y'] <= upper_bound)]

    df_cleaned['ds'] = pd.to_datetime(df_cleaned['ds'])

    spike_period = pd.DataFrame({
        'holiday': 'spike_event',
        'ds': pd.date_range(start='2022-04-01', end='2022-11-01')
    })

    years = list(df_cleaned['ds'].dt.year.unique())
    years = sorted(set(years + [2022]))
    no_holidays = holidays.CountryHoliday('NO', years=years)

    norway_df = (
        pd.DataFrame([
            {'ds': pd.to_datetime(d), 'holiday': name}
            for d, name in no_holidays.items()
        ])
    )

    all_holidays = pd.concat([norway_df, spike_period], ignore_index=True)

    m = Prophet(
        interval_width=0.90,
        seasonality_mode='multiplicative',
        changepoint_prior_scale=0.2,
        holidays=all_holidays
    )
    m.fit(df_cleaned)

    future = m.make_future_dataframe(periods=300)

    future = future[~future['ds'].dt.dayofweek.isin([5, 6])]

    future = future.reset_index(drop=True)

    forecast = m.predict(future)

    forecast['yhat'] = forecast['yhat'].clip(lower=0)
    forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
    forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)
    forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].to_csv('../caseArrival/Forecast.csv')
    print(f"new forecast made with date{date}")
