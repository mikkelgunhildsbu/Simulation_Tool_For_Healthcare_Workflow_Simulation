import pandas as pd
import math

from simSetup.resource_initlializer import get_half_or_full_day

_MIN_COUNTS = {
    'accessioning': 0,
    'grossing': 10,
    'manualEmbedding': 30,
    'manualStaining': 30,
    'manualSectioning': 20,
    'decalcination': 0,
    'finalReportFinished': 0,
}

_MACHINE_SPECS = {
    'scanning': {'batch_size': 25, 'batch_time_h': 15 / 60},
    'automaticStaining': {'batch_size': 25, 'batch_time_h': 60 / 60},
    'stainingIHC': {'batch_size': 25, 'batch_time_h': 60 / 60},
    'automaticEmbedding': {'batch_size': 25, 'batch_time_h': 25 / 60},
    'processing': {'batch_size': 125, 'batch_time_h': (14.5 * 60) / 60},
}


def _qualified_actors_for_window(df_window: pd.DataFrame, activity: str):
    df_act = df_window[
        (df_window['activity'] == activity) &
        ((df_window['event_type'] == 2) |
         (df_window['event_name'].isin([99, 91, 92, 93])))
        ]
    required = _MIN_COUNTS.get(activity, 0)
    full, half = [], []
    for actor, grp in df_act.groupby('actor_ref'):
        if len(grp) < required:
            continue
        first, last = grp['happened_at'].min(), grp['happened_at'].max()
        shift = get_half_or_full_day(first, last)
        if shift == 'half_day':
            half.append(int(actor))
        else:
            full.append(int(actor))
    return sorted(full), sorted(half)


def _required_machines_for_window(df_window: pd.DataFrame, specs: dict, window_hours: float) -> dict:
    counts = df_window['activity'].value_counts().to_dict()
    workday_h = min(window_hours, 8)
    result = {}
    for act, spec in specs.items():
        total = counts.get(act, 0)
        if total == 0:
            result[act] = 0
            continue
        bs = spec['batch_size']
        bt = spec['batch_time_h']
        batches = math.ceil(total / bs)
        if act == "processing":
            result[act] = batches

        else:
            total_machine_h = batches * bt
            machines_frac = total_machine_h / workday_h if workday_h > 0 else float('inf')
            result[act] = math.floor(machines_frac) + 1

    return result


def generate_daily_configs(
        event_log: pd.DataFrame,
        window_start: pd.Timestamp,
        num_days: int
) -> list[dict]:
    df = event_log.copy()
    df['happened_at'] = pd.to_datetime(df['happened_at'])
    configs = []
    for d in range(num_days):
        start = window_start + pd.Timedelta(days=d)
        end = start + pd.Timedelta(days=1)
        win = df[(df['happened_at'] >= start) & (df['happened_at'] < end)]
        cfg = {}
        # actors
        for act, attr in [
            ('accessioning', 'accessioning_nurses'),
            ('grossing', 'grossing_nurses'),
            ('decalcination', 'decalcination_nurses'),
            ('manualEmbedding', 'manualEmbedding_nurses'),
            ('manualStaining', 'manualStaining_nurses'),
            ('manualSectioning', 'manualSectioning_nurses'),
            ('finalReportFinished', 'finalReportFinished_nurses'),
        ]:
            full, half = _qualified_actors_for_window(win, act)
            cfg[attr] = full
            cfg[attr + '_half'] = half
        window_h = (end - start).total_seconds() / 3600
        machines = _required_machines_for_window(win, _MACHINE_SPECS, window_h)
        cfg['num_scanning_machines'] = machines.get('scanning', 0)
        cfg['num_staining_machines'] = machines.get('automaticStaining', 0)
        cfg['num_stainingIHC_machines'] = machines.get('stainingIHC', 0)
        cfg['num_automatic_embedding_machines'] = machines.get('automaticEmbedding', 0)
        cfg['num_processing_machines'] = machines.get('processing', 0)

        configs.append(cfg)
    return configs
