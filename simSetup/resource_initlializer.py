from datetime import datetime

import pandas as pd
import math

from pytz import FixedOffset

from global_parameters import GlobalParameters as g


def update_machines_from_day(event_log,
                             end_date_str,
                             start_date_str):
    """
    Updates machines from day. Uses the batch size and service time to calculate how many machines are needed to meet
    that days throughput for each machine.
    :param event_log:
    :param end_date_str:end date for update
    :param start_date_str: start date for update
    return:
    """
    event_log['happened_at'] = pd.to_datetime(event_log['happened_at'])
    start_date = pd.Timestamp(start_date_str)
    end_date = pd.Timestamp(end_date_str)

    yesterday_log = event_log[
        (event_log['happened_at'] >= start_date) &
        (event_log['happened_at'] < end_date)
        ]

    counts = yesterday_log['activity'].value_counts().to_dict()

    specs = {
        'scanning': {'batch_size': 25, 'batch_time_h': 15 / 60},
        'automaticStaining': {'batch_size': 25, 'batch_time_h': 60 / 60},
        'stainingIHC': {'batch_size': 25, 'batch_time_h': 60 / 60},
        'automaticEmbedding': {'batch_size': 25, 'batch_time_h': 25 / 60},
        'processing': {'batch_size': 125, 'batch_time_h': 14.5 * 60 / 60},
    }

    window_hours = (end_date - start_date).total_seconds() / 3600
    workday_hours = min(window_hours, 8)

    required = {}
    for act, spec in specs.items():
        total_items = counts.get(act, 0)
        if total_items == 0:
            required[act] = 0
            continue

        bs = spec['batch_size']
        bt = spec['batch_time_h']
        num_batches = math.ceil(total_items / bs)
        total_machine_h = num_batches * bt

        machines_frac = total_machine_h / workday_hours if workday_hours > 0 else float('inf')

        lower = math.floor(machines_frac)

        required[act] = lower + 1

    g.num_scanning_machines = required['scanning']
    g.num_staining_machines = required['automaticStaining']
    g.num_stainingIHC_machines = required['stainingIHC']
    g.num_automatic_embedding_machines = required['automaticEmbedding']
    g.num_processing_machines = required['processing']


def get_half_or_full_day(firstActivity, lastActivity):
    hours_worked = (lastActivity - firstActivity).total_seconds() / 3600
    if hours_worked < 4.5:
        return "half_day"
    else:
        return "full_day"


def update_actors_from_yesterday(event_log, date, start_date):
    event_log['happened_at'] = pd.to_datetime(event_log['happened_at'])
    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(date)
    yesterday_log = event_log[(event_log['happened_at'] < end_date) &
                              (event_log['happened_at'] > start_date)]

    min_counts = {
        'accessioning': 0,
        'grossing': 10,
        'manualEmbedding': 30,
        'manualStaining': 30,
        'manualSectioning': 20,
    }

    def get_qualified_actors_with_shift(activity_name):
        df = yesterday_log[
            (yesterday_log['activity'] == activity_name) &
            ((yesterday_log['event_type'] == 2) | (yesterday_log['event_name'].isin([99, 91, 93])))
            ]
        required_count = min_counts.get(activity_name, 0)
        grouped = df.groupby('actor_ref')
        qualified_full = []
        qualified_half = []
        for actor, group in grouped:
            if len(group) >= required_count:
                first_activity = group['happened_at'].min()
                last_activity = group['happened_at'].max()
                shift = get_half_or_full_day(first_activity, last_activity)
                if shift == "half_day":
                    qualified_half.append(round(int(actor), 0))
                else:
                    qualified_full.append((round(int(actor), 0)))
        return qualified_full, qualified_half

    full_acc, half_acc = get_qualified_actors_with_shift('accessioning')
    g.manualSectioning_nurses, g.manualSectioning_nurses_half = get_qualified_actors_with_shift('manualSectioning')
    g.grossing_nurses, g.grossing_nurses_half = get_qualified_actors_with_shift('grossing')
    g.decalcination_nurses, g.decalcination_nurses_half = get_qualified_actors_with_shift('decalcination')
    g.manualEmbedding_nurses, g.manualEmbedding_nurses_half = get_qualified_actors_with_shift('manualEmbedding')
    g.manualStaining_nurses, g.manualStaining_nurses_half = get_qualified_actors_with_shift('manualStaining')
    g.finalReportFinished_nurses, g.finalReportFinished_nurses_half = get_qualified_actors_with_shift(
        'finalReportFinished')

    g.accessioning_nurses = full_acc
    g.accessioning_nurses_half = half_acc
