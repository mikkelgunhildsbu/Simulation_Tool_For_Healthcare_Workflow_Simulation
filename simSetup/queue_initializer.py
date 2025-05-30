import pandas as pd

from entities import CaseEntity, SlideEntity, BlockEntity
from utilities.sim_utils import is_within_working_hours


def get_last_activity_group(event_log):
    event_log = event_log[
        (event_log['event_type'] == 2) |
        (event_log['event_name'] == 99) |
        (event_log['event_name'] == 91) |
        (event_log['event_name'] == 92) |
        (event_log['event_name'] == 93)|
        (event_log['event_name'] == 101)|
        (event_log['event_name'] == 102)|
        (event_log['event_name'] == 110)
    ].copy()

    event_log['happened_at'] = pd.to_datetime(event_log['happened_at'])
    event_log.sort_values(by=['case_id', 'happened_at'], inplace=True)

    def keep_last_consecutive_activity(group):
        final_activity = group.iloc[-1]['activity']
        idx = len(group) - 1
        while idx >= 0 and group.iloc[idx]['activity'] == final_activity:
            idx -= 1
        result = group.iloc[idx + 1:]
        return result

    last_activity_groups = (
        event_log
            .groupby('case_id', group_keys=False)
            .apply(keep_last_consecutive_activity)
    )

    return last_activity_groups

def initialize_from_event_log(event_log, queues):
    """
    Initializes queues with the last finished "activity group" of each case

    :param event_log: The event log used
    :param queues: Queues that are filled
    :return:
    """
    event_log = event_log.copy()
    df_last = get_last_activity_group(event_log)

    activity_to_next_queue = {
        "specimenTaken":              "accessioning_queue",
        "accessioning":               "grossing_queue",
        "grossing":                   "processing_queue",
        "processing":                 "embedding_queue",
        "manualEmbedding":            "manual_sectioning_queue",
        "automaticEmbedding":         "manual_sectioning_queue",
        "manualSectioning":           "staining_queue",
        "automaticStaining":          "scanning_queue",
        "manualStaining":             "scanning_queue",
        "specialStainRequested":      "manual_sectioning_queue",
        "stainingIHC":                "scanning_queue",
        "additionalGrossingRequested":"grossing_queue",
        "ihcRequested":               "manual_sectioning_queue",
        "scanning":                   "final_report_queue",
    }
    df_last = df_last.assign(
        next_queue = df_last['activity'].map(activity_to_next_queue)
    )

    cases = {}
    for cid, grp in df_last.groupby('case_id', sort=False):
        case = CaseEntity(cid)
        acc = event_log[
            (event_log['case_id'] == cid) &
            (event_log['activity'] == 'accessioning') &
            (event_log['event_type'] == 1)
        ]
        if not acc.empty:
            case.start_time = pd.to_datetime(acc['happened_at']).min()
        first = grp.iloc[0]
        case.specimen_containers = first['specimen_containers']
        case.specimen_type       = first['specimen_typ']
        cases[cid] = case

    seen_final = set()
    for row in df_last.itertuples(index=False):
        cid, activity, tok_type, tok_id, nq = (
            row.case_id,
            row.activity,
            row.token_type,
            row.token_id,
            row.next_queue
        )
        case = cases[cid]

        if activity == 'scanning':
            slide = SlideEntity(case)
            slide.token_id = tok_id
            case.scanned_slides += 1
            if cid not in seen_final:
                queues['final_report_queue'].put(case)
                seen_final.add(cid)
            continue

        if not isinstance(nq, str):
            continue

        if tok_type == 2 or activity in ('grossing', 'processing'):
            block = BlockEntity(case)
            block.token_id = tok_id
            queues[nq].put(block)

        elif activity == 'ihcRequested':
            block = BlockEntity(case)
            block.token_id = tok_id
            case.stainingIHC = True
            queues[nq].put(block)

        elif activity == 'additionalGrossingRequested':
            case.grossing_rework = True
            queues[nq].put(case)

        elif activity == 'specialStainRequested':
            block = BlockEntity(case)
            block.token_id = tok_id
            queues[nq].put(block)

        elif tok_type == 3 or activity == 'manualSectioning':
            slide = SlideEntity(case)
            slide.token_id = tok_id
            queues[nq].put(slide)

        elif activity == 'accessioning':
            queues[nq].put(case)

    last_ts = pd.to_datetime(event_log['happened_at'].max())
    if not is_within_working_hours(last_ts, 0):
        last_ts = last_ts.replace(hour=8, minute=0, second=0, microsecond=0)
    return last_ts

