import os
import joblib
import numpy as np
import scipy.stats as stats
import pandas as pd
import random
from scipy.stats import lognorm

"""
Utilities for different functionalities in stages 
"""

# Static Files
rework_df = pd.read_csv('components/rework/counts_pivot.csv')
specimen_type_df = pd.read_csv('components/caseAttributes/specimen_typ_distribution.csv')
specimenContainerData = pd.read_csv('components/caseAttributes/specimen_containers_empirical_distribution.csv')

regressor_loaded = joblib.load('components/caseSplitting/decision_tree_regressor.joblib')
encoded_columns = joblib.load('components/caseSplitting/encoded_columns.joblib')

df_forecast = None
df_forecast_last_modified = None
_forecast_csv = "components/caseArrivals/Forecast.csv"

_actor_dis_df = None
_actor_dis_last_modified = None
_csv_path = 'components/serviceTimes/actor_speeds.csv'


"""
Function to check rework 
"""


def checkRework(specimen_type):
    if rework_df.index.name != 'specimen_typ':
        rework_df.set_index('specimen_typ', inplace=True)
    specimen_type = specimen_type.strip()

    if specimen_type not in rework_df.index:
        return 99

    counts = rework_df.loc[specimen_type]
    total = counts.sum()

    if total == 0:
        return int(99)

    probabilities = counts / total

    selected_event = np.random.choice(probabilities.index, p=probabilities.values)
    return int(selected_event)


"""
Function to get "random" specimen type
"""


def getSpecimenType():
    specimen_types = specimen_type_df['specimen_typ'].tolist()
    weights = specimen_type_df['case_count'].tolist()
    selected_specimen = random.choices(specimen_types, weights=weights, k=1)[0]
    return selected_specimen


"""
Function to get "random" number of specimen containers
"""


def getSpecimenContainer(specimen_type):
    df = specimenContainerData
    sub = df[df["specimen_typ"] == specimen_type]
    if sub.empty:
        return 1

    containers = sub["specimen_containers"].tolist()
    weights = sub["weight"].tolist()

    return random.choices(containers, weights=weights, k=1)[0]


"""
Get number of blocks form decision tree
"""


def num_blocks_generator(case):
    test_example = pd.DataFrame({
        'specimen_containers': [case.specimen_containers],
        'specimen_typ': [case.specimen_type]
    })
    test_encoded = pd.get_dummies(test_example, columns=['specimen_typ'], drop_first=False)
    missing_cols = [col for col in encoded_columns if col not in test_encoded.columns]
    missing_df = pd.DataFrame({col: [0] for col in missing_cols})
    test_encoded = pd.concat([test_encoded, missing_df], axis=1)
    test_encoded = test_encoded[encoded_columns]
    reg_pred = regressor_loaded.predict(test_encoded)
    num_blocks = round(reg_pred[0])

    return num_blocks


def get_cases_per_day(sim_start_time, sim_time=0):
    """Get number of cases for each day"""
    global df_forecast, df_forecast_last_modified
    try:
        current_modified = os.path.getmtime(_forecast_csv)
        if df_forecast is None or df_forecast_last_modified != current_modified:
            df_forecast = pd.read_csv(_forecast_csv)
            df_forecast_last_modified = current_modified
    except FileNotFoundError:
        return 250
    current_date = (sim_start_time + pd.Timedelta(days=sim_time)).date()
    df_forecast["ds"] = pd.to_datetime(df_forecast["ds"]).dt.date

    if current_date in df_forecast["ds"].values:
        row = df_forecast.loc[df_forecast["ds"] == current_date]

        yhat_lower = row["yhat_lower"].values[0]
        yhat_upper = row["yhat_upper"].values[0]

        arrivals_today = int(round(random.uniform(yhat_lower, yhat_upper)))

    else:
        arrivals_today = 0

    return arrivals_today




def get_sampled_duration(actor_ref, activity):
    """

    :param actor_ref:
    :param activity:
    :return:
    """
    global _actor_dis_df, _actor_dis_last_modified

    try:
        current_modified = os.path.getmtime(_csv_path)

        if _actor_dis_df is None or _actor_dis_last_modified != current_modified:
            _actor_dis_df = pd.read_csv(_csv_path)
            _actor_dis_last_modified = current_modified

    except FileNotFoundError:
        return 30

    row = _actor_dis_df[
        (_actor_dis_df['actor_ref'] == actor_ref) & (_actor_dis_df['activity'] == activity)
        ]

    if not row.empty:
        shape, loc, scale = row.iloc[0]['shape'], row.iloc[0]['loc'], row.iloc[0]['scale']
        return lognorm.rvs(shape, loc=loc, scale=scale)
    else:
        rows = _actor_dis_df[
            (_actor_dis_df['activity'] == activity) #& (_actor_dis_df['speed_level'] == 'medium')
            ]
        if not rows.empty:
            s, loc, sc = rows.iloc[0][['shape', 'loc', 'scale']]
            return lognorm.rvs(s, loc=loc, scale=sc)
        else:
            return 30
