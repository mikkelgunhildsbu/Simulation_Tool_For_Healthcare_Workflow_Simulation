import numpy as np
import pandas as pd
import scipy.stats as stats

"""
Implementation of service time distributions
"""
"""
Cleans the log aggregating one activity into one row with start and finish time
"""


def clean_event_log(event_log):
    event_log['happened_at'] = pd.to_datetime(event_log['happened_at'])

    events_df = event_log[event_log['event_type'] == 0].copy()
    activities_df = event_log[event_log['event_type'] != 0].copy()

    activities_df = activities_df.sort_values(['case_id', 'token_id', 'activity', 'happened_at'])
    activities_df['activity_instance_counter'] = (
        activities_df.groupby(['case_id', 'token_id', 'activity'])['event_type']
            .transform(lambda x: x.eq(1).cumsum())
    )
    activities_df['activity_instance_id'] = activities_df.groupby(
        ['case_id', 'token_id', 'activity', 'activity_instance_counter']
    ).ngroup()

    pivot = activities_df.pivot_table(
        index='activity_instance_id',
        columns='event_type',
        values='happened_at',
        aggfunc='first'
    ).reset_index()
    pivot.columns.name = None
    pivot = pivot.rename(columns={1: 'start_time', 2: 'finish_time'})

    info = activities_df[['activity_instance_id', 'case_id', 'token_id', 'activity', 'actor_ref']].drop_duplicates(
        'activity_instance_id')
    activities_pivot = pivot.merge(info, on='activity_instance_id', how='left')

    events_df = events_df.rename(columns={'happened_at': 'finish_time'})
    events_df['start_time'] = events_df['finish_time']

    cols = ['case_id', 'token_id', 'activity', 'actor_ref', 'start_time', 'finish_time']
    full_log = pd.concat([activities_pivot[cols], events_df[cols]], ignore_index=True)
    full_log = full_log.sort_values(['case_id', 'finish_time'])

    return full_log


"""
Calculate durations 
Divides manual sectioning durations by corresponding batch size 
Sets start time to last finish time 
"""


def update_service_time(event_log):
    print("Loading and cleaning event log...")
    df_clean = clean_event_log(event_log)
    print(f"Cleaned log contains {len(df_clean)} records.")

    event_log = df_clean.copy()
    event_log['start_time'] = pd.to_datetime(event_log['start_time'])
    event_log['finish_time'] = pd.to_datetime(event_log['finish_time'])
    event_log['duration_minutes'] = (event_log['finish_time'] - event_log['start_time']).dt.total_seconds() / 60
    event_log = event_log[event_log['duration_minutes'] > 0].copy()

    manual_mask = event_log['activity'] == 'manualSectioning'
    manual = event_log[manual_mask].copy()
    other = event_log[~manual_mask].copy()

    if not manual.empty:
        manual['batch_key'] = manual.groupby(['actor_ref', 'start_time', 'finish_time']).ngroup()
        batch_sizes = manual.groupby('batch_key').size()
        manual['batch_size'] = manual['batch_key'].map(batch_sizes)
        manual['duration_minutes'] /= manual['batch_size']

    filtered = pd.concat([manual, other], ignore_index=True)
    filtered = filtered.sort_values(by=['actor_ref', 'start_time']).copy()

    filtered = filtered[filtered['start_time'].dt.date == filtered['finish_time'].dt.date]

    def update_start_times(group):
        group = group.sort_values('start_time').copy()
        for i in range(1, len(group)):
            prev = group.iloc[i - 1]
            curr = group.iloc[i]

            if curr['activity'] != 'manualSectioning':
                if curr['start_time'].date() == prev['finish_time'].date():
                    group.loc[group.index[i], 'start_time'] = prev['finish_time']
                    group.loc[group.index[i], 'duration_minutes'] = (
                            (curr['finish_time'] - prev['finish_time']).total_seconds() / 60
                    )
            if curr['activity'] == 'manualSectioning':
                if curr['start_time'].date() == prev['finish_time'].date():
                    group.loc[group.index[i], 'duration_minutes'] = curr['duration_minutes'] + (
                                (curr['start_time'] - prev['finish_time']).total_seconds() / 60) / curr['batch_size']

        return group

    filtered = filtered.groupby('actor_ref', group_keys=False).apply(update_start_times)
    filtered = filtered[filtered['duration_minutes'] > 0].copy()
    filtered['duration_hours'] = filtered['duration_minutes'] / 60

    def adjust_workday(group):
        group = group.copy()
        total_h = group['duration_hours'].sum()

        if 1 < total_h < 8:
            target_hours = 8
        else:
            return group

        start_day = group['start_time'].min()
        target_mark = start_day + pd.Timedelta(hours=target_hours)
        last_finish = group['finish_time'].max()

        last_mask = group['finish_time'] == last_finish
        manual_batch = last_mask & (group['activity'] == 'manualSectioning')
        to_adjust = manual_batch if manual_batch.any() else last_mask

        n_rows = to_adjust.sum()
        if n_rows == 0:
            return group

        extra_secs_total = (target_mark - last_finish).total_seconds()
        extra_per_row_secs = extra_secs_total / n_rows

        group.loc[to_adjust, 'finish_time'] = target_mark
        group.loc[to_adjust, 'duration_minutes'] += extra_per_row_secs / 60
        group.loc[to_adjust, 'duration_hours'] += extra_per_row_secs / 3600

        return group

    """
    manual_sectioning = filtered[filtered['activity'] == 'manualSectioning'].copy()
    adjusted_manual = (
        manual_sectioning.groupby(['actor_ref', manual_sectioning['start_time'].dt.date], group_keys=False)
            .apply(adjust_workday)
            .reset_index(drop=True)
    )

    others = filtered[filtered['activity'] != 'manualSectioning'].copy()
    adj = pd.concat([adjusted_manual, others], ignore_index=True)"""

    adj = filtered
    adj = adj[adj['duration_minutes'] > 0].copy()

    actor_activity_means = (
        adj.groupby(['actor_ref', 'activity'])['duration_minutes']
            .mean()
            .reset_index(name='avg_duration_minutes')
    )

    def label_speeds(group):
        q1, q2 = group['avg_duration_minutes'].quantile([1 / 3, 2 / 3])

        def lbl(x):
            return 'fast' if x <= q1 else ('medium' if x <= q2 else 'slow')

        group['speed_level'] = group['avg_duration_minutes'].apply(lbl)
        return group

    actor_speeds = (
        actor_activity_means
            .groupby('activity', group_keys=False)
            .apply(label_speeds)
    )

    durations_list = (
        adj.groupby(['actor_ref', 'activity'])['duration_minutes']
            .apply(list)
            .reset_index(name='all_durations')
    )

    actor_speeds = actor_speeds.merge(durations_list, on=['actor_ref', 'activity'], how='left')

    records = []

    """
    Assigns durations to each activity "and" each speed level
    """
    for activity in actor_speeds['activity'].unique():
        for level in ['fast', 'medium', 'slow']:
            sub = actor_speeds[(actor_speeds['activity'] == activity)]  # & (actor_speeds['speed_level'] == level)]
            if sub.empty:
                continue

            durations = [d for lst in sub['all_durations'] for d in lst]
            # durations = trim_percentiles(durations)

            if len(durations) < 1:
                continue

            arr = np.array(durations)
            positive = arr[arr > 0]
            shape, loc, scale = stats.lognorm.fit(positive, floc=0)

            records.append({
                'activity': activity,
                'speed_level': level,
                'n_samples': len(durations),
                'shape': shape,
                'loc': loc,
                'scale': scale
            })

    level_dist_fits = pd.DataFrame(records)

    lookup = level_dist_fits[['activity', 'speed_level', 'shape', 'loc', 'scale']]
    actor_speeds = actor_speeds.merge(lookup, on=['activity', 'speed_level'], how='left')
    actor_speeds = actor_speeds.drop(columns=['speed_level','avg_duration_minutes', 'all_durations'], errors='ignore')

    #actor_speeds = actor_speeds.merge(lookup, on=['activity, speed_level'], how='left')

    actor_speeds.to_csv('components/serviceTimes/actor_speeds.csv', index=False)

    return actor_speeds
