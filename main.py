import copy
import pandas as pd
import simpy
from datetime import datetime


from utilities.get_event_log import get_log
from global_parameters import GlobalParameters as g
from pathology_model import PathologyModel
from simSetup.queues import create_queues

from simSetup.queue_initializer import initialize_from_event_log


use_queue = True


def build_initial_queue(event_log):
    env = simpy.Environment()
    queues = create_queues(env)
    sim_start = initialize_from_event_log(event_log, queues)
    plain_q = {qn: list(store.items) for qn, store in queues.items()}
    return sim_start, plain_q


def run_day(start_time, carry_in_queue=None):
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

    carry_q = {qn: list(store.items) for qn, store in pm.queue_afters.items()}
    queue_lengths = pm.queue_after
    return carry_q, pm.results_df, queue_lengths

def main():

    today = datetime.now()
    if use_queue:
        event_log = get_log(today, today - pd.Timedelta(weeks=4))
        sim_start_time, initial_queue = build_initial_queue(event_log)
    else:
        sim_start_time = today
        initial_queue = None

    safe_ts = sim_start_time.strftime("%Y-%m-%d_%H-%M-%S")


    all_logs = []
    all_throughput = []
    all_queue_lengths = []
    all_tat_stats = []

    for run_id in range(g.number_of_runs):
        print(f"\n=== Run {run_id + 1} ===")
        carry_queue = initial_queue

        for day_offset in range(g.sim_days):
            day_start = sim_start_time + pd.Timedelta(days=day_offset)

            carry_queue, result_df, queue_length = run_day(day_start, carry_queue)

            if result_df is not None:
                result_df['run'] = run_id
                result_df['day'] = day_offset + 1
                result_df['date'] = day_start.date()
                all_logs.append(result_df)

                tp = (
                    result_df['Activity']
                    .value_counts()
                    .rename_axis('activity')
                    .reset_index(name='throughput')
                )
                tp['run'] = run_id
                tp['day'] = day_offset + 1
                tp['date'] = day_start.date()
                all_throughput.append(tp)

                tat = result_df['Turnaround_time']
                stats = {
                    'run': run_id,
                    'day': day_offset + 1,
                    'tat_count': tat.count(),
                    'tat_mean': tat.mean(),
                    'tat_median': tat.median(),
                    'tat_min': tat.min(),
                    'tat_max': tat.max(),
                    'tat_std': tat.std(),
                    'tat_p90': tat.quantile(0.9),
                }
                all_tat_stats.append(stats)

                ql = pd.DataFrame([
                    {'queue_name': qn, 'queue_length': length}
                    for qn, length in queue_length.items()
                ])
                ql['run'] = run_id
                ql['day'] = day_offset + 1
                ql['date'] = day_start.date()
                all_queue_lengths.append(ql)

    df = pd.concat(all_logs, ignore_index=True)
    df.to_csv(f"sim_logs_example.csv", index=False)

    tp_df = pd.concat(all_throughput, ignore_index=True)
    #tp_df.to_csv(f"sim_throughput_{safe_ts}.csv", index=False)

    ql_df = pd.concat(all_queue_lengths, ignore_index=True)
    #ql_df.to_csv(f"sim_queue_lengths_{safe_ts}.csv", index=False)

    tat_df = pd.DataFrame(all_tat_stats)
    #tat_df.to_csv(f"sim_tat_{safe_ts}.csv", index=False)

    print(f"Simulation complete for {sim_start_time.date()}. Files saved with timestamp: {safe_ts}")

if __name__ == "__main__":
    main()
