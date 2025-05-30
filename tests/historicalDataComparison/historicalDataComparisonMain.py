import os
import pickle
import copy

import pandas as pd
import simpy

from components.caseArrivals.get_case_arrival_for_X_date import getForcast
from components.serviceTimes.calculate_service_times import update_service_time
from global_parameters import GlobalParameters as g
from pathology_model import PathologyModel
from simSetup.queues import create_queues
from simSetup.queue_initializer import initialize_from_event_log
from tests.historicalDataComparison.dailyConfigs import generate_daily_configs
from utilities.get_event_log import get_log

g.number_of_runs = 20
num_days = 3


def build_initial_queue(event_log, QUEUE_CACHE):
    env = simpy.Environment()
    queues = create_queues(env)
    sim_start = initialize_from_event_log(event_log, queues)
    plain_q = {qn: list(store.items) for qn, store in queues.items()}

    with open(QUEUE_CACHE, "wb") as f:
        pickle.dump((sim_start, plain_q), f)
    return sim_start, plain_q


def run_day(start_time, config, carry_in_queue=None):
    for attr, val in config.items():
        setattr(g, attr, val)

    env = simpy.Environment()
    queues = create_queues(env)
    if carry_in_queue:
        for qn, items in carry_in_queue.items():
            for it in items:
                queues[qn].put(copy.deepcopy(it))

    pm = PathologyModel(
        run_number=0,
        sim_start_time=start_time,
        queues=queues,
        env=env
    )
    pm.run()

    logs = [pm.results_df]
    carry_q = {qn: list(store.items) for qn, store in pm.queue_afters.items()}
    queue_lengths = pm.queue_after
    return carry_q, logs, queue_lengths


def main():
    sim_start_dates = [
        '2024-06-17 07:00:00',
        '2024-09-16 07:00:00',
        '2023-03-21 07:00:00',
        '2023-11-01 07:00:00',
        '2024-02-05 07:00:00',
        '2024-10-14 07:00:00',
        '2025-01-15 07:00:00',
        '2024-03-04 07:00:00',
        '2023-05-08 07:00:00',
        '2025-04-22 07:00:00'
    ]
    total_throughput = []

    for date_str in sim_start_dates:
        date = pd.to_datetime(date_str)
        safe_ts = date.strftime("%Y-%m-%d_%H-%M-%S")
        QUEUE_CACHE = f"queues/initial_queue_{safe_ts}.pkl"

        event_log = get_log(date, date - pd.Timedelta(weeks=12))

        update_service_time(event_log)
        getForcast(date)
        if os.path.exists(QUEUE_CACHE):
            print("Loading cached initial queue…")
            with open(QUEUE_CACHE, "rb") as f:
                sim_start_time, initial_queue = pickle.load(f)
                queue_before = {queue_name: len(store) for queue_name, store in initial_queue.items()}

                print(queue_before)
        else:
            print("Cache miss; running state initializer…")
            sim_start_time, initial_queue = build_initial_queue(event_log, QUEUE_CACHE)

        his_event_log = get_log(date + pd.Timedelta(weeks=4, days=1), date)

        config_log = his_event_log[
            ((his_event_log['event_type'] == 2) | his_event_log['event_name'].isin([99, 91, 92, 93]))
            ]

        daily_configs = generate_daily_configs(
            config_log,
            window_start=sim_start_time.replace(hour=8, minute=0),
            num_days=num_days
        )

        master_log = []
        master_throughput = []
        master_queue_lengths = []
        master_tat_stats = []
        hist_throughput = []
        historical_queue = []

        for day_offset in range(num_days):

            date_after = date + pd.Timedelta(days=day_offset + 1)
            safe_ts_after = date_after.strftime("%Y-%m-%d_%H-%M-%S")
            QUEUE_AFTER_CACHE = f"queues/initial_queue_{safe_ts_after}.pkl"
            log_after = get_log((date_after), date_after - pd.Timedelta(weeks=5))

            print(f"Loading queue after... for {date + pd.Timedelta(days=day_offset + 1)}")
            if day_offset in [0, 1, 2, 4, 13 ,27]:
                if os.path.exists(QUEUE_AFTER_CACHE):
                    print("Loading cached initial queue…")
                    with open(QUEUE_AFTER_CACHE, "rb") as f:
                        _, queue_after = pickle.load(f)

                else:
                    print("Cache miss; running state initializer…")
                    _, queue_after = build_initial_queue(log_after, QUEUE_AFTER_CACHE)

                queue_after = {queue_name: len(store) for queue_name, store in queue_after.items()}

                his_ql = pd.DataFrame([
                    {'queue_name': qn, 'historical_length': length}
                    for qn, length in queue_after.items()
                ])
                his_ql['day'] = day_offset + 1
                his_ql['date'] = date + pd.Timedelta(days=day_offset)
                historical_queue.append(his_ql)

            day_start = sim_start_time + pd.Timedelta(days=day_offset)
            window_start = day_start.replace(hour=8, minute=0)
            window_end = window_start + pd.Timedelta(days=1)

            day_hist = his_event_log[
                (his_event_log['happened_at'] >= window_start) &
                (his_event_log['happened_at'] < window_end) &
                ((his_event_log['event_type'] == 2) | his_event_log['event_name'].isin([99, 91, 92, 93]))
                ]

            hist_tp = (
                day_hist
                    .groupby('activity')
                    .size()
                    .rename('hist_throughput')
                    .reset_index()
            )
            hist_tp['day'] = day_offset + 1
            hist_tp['date'] = date + pd.Timedelta(days=day_offset)
            hist_throughput.append(hist_tp)

        for run_id in range(g.number_of_runs):
            print(f"\n=== Run {run_id + 1} ===")
            carry_queue = initial_queue

            for day_offset in range(num_days):
                day_start = sim_start_time + pd.Timedelta(days=day_offset)
                cfg = daily_configs[day_offset]

                carry_queue, day_logs, queue_length = run_day(day_start, cfg, carry_queue)

                if day_logs:
                    day_df = pd.concat(day_logs, ignore_index=True)
                    day_df['run'] = run_id
                    day_df['day'] = day_offset + 1
                    master_log.append(day_df)

                    tp = (
                        day_df['Activity']
                            .value_counts()
                            .rename_axis('activity')
                            .reset_index(name='throughput')
                    )
                    tp['run'] = run_id
                    tp['day'] = day_offset + 1
                    tp['date'] = date + pd.Timedelta(days=day_offset)
                    master_throughput.append(tp)

                    tat = day_df['Turnaround_time']
                    stats = {
                        'run': run_id,
                        'day': day_offset + 1,
                        'tat_count': tat.count(),
                        'tat_mean': tat.mean(),
                        'tat_median': tat.median(),
                        'tat_min': tat.min(),
                        'tat_mac': tat.max(),
                        'tat_std': tat.std(),
                        'tat_p90': tat.quantile(0.9),
                    }
                    master_tat_stats.append(stats)

                ql = pd.DataFrame([
                    {'queue_name': qn, 'queue_length': length}
                    for qn, length in queue_length.items()
                ])
                ql['run'] = run_id
                ql['date'] = date + pd.Timedelta(days=day_offset)
                ql['day'] = day_offset + 1
                master_queue_lengths.append(ql)

        hist_tp_df = pd.concat(hist_throughput, ignore_index=True)
        historical_que = pd.concat(historical_queue, ignore_index=True)
        historical_que.to_csv('test.csv')
        th_df = pd.concat(master_throughput, ignore_index=True)
        df = pd.concat(master_log, ignore_index=True)
        ql_df = pd.concat(master_queue_lengths, ignore_index=True)
        master_tat_df = pd.DataFrame(master_tat_stats)

        agg_tp = (
            th_df
                .groupby(['date', 'day', 'activity'])['throughput']
                .agg(['min', 'max', 'mean'])
                .reset_index()
                .rename(columns={
                'min': 'throughput_min',
                'max': 'throughput_max',
                'mean': 'throughput_mean'
            })
        )

        agg_ql = (
            ql_df
                .groupby(['day', 'date', 'queue_name'])['queue_length']
                .agg(['min', 'max', 'mean'])
                .reset_index()
                .rename(columns={
                'min': 'length_min',
                'max': 'length_max',
                'mean': 'length_mean'
            })
        )

        combined_tp = agg_tp.merge(
            hist_tp_df,
            on=['date', 'day', 'activity'],
            how='left'
        )

        combined_ql = agg_ql.merge(
            historical_que,
            on=['date', 'day', 'queue_name'],
            how='left'
        )

        combined_ql.to_csv(f'QL/simulation_combined_ql{safe_ts}.csv', index=False)
        #df.to_csv(f"DF/simulation_df_{safe_ts}.csv", index=False)
        ##agg_ql.to_csv(f"simulation_ql_{safe_ts}.csv", index=False)
        combined_tp.to_csv(f"TP/combined_th_{safe_ts}.csv", index=False)
        #master_tat_df.to_csv(f"TAT/master_tat_{safe_ts}.csv", index = False)
        total_throughput.append(combined_tp)

        print(f"Saved combined stats for {date_str} → simulation_stats_{safe_ts}.csv")

    total_tp = pd.concat(total_throughput, ignore_index=True)
    total_tp.to_csv('total.csv', index=False)


if __name__ == "__main__":
    df_stats = main()
