# base_stage.py
import os
from datetime import timedelta

import pandas as pd
from scipy.stats import lognorm

from utilities.sim_utils import convert_to_real_time
from utilities.stage_utilites import get_sampled_duration


class BaseStage:
    """
        Base Stage for stages in pathology department
    """

    def __init__(self, env, queues, resources, sim_start_time, log_entries, g):
        self.env = env
        self.queues = queues
        self.resources = resources
        self.sim_start_time = sim_start_time
        self.log_entries = log_entries
        self.g = g

        self.half_day = g.accessioning_nurses_half + g.grossing_nurses_half + g.manualEmbedding_nurses_half + g.manualSectioning_nurses_half + g.finalReportFinished_nurses

    def wait_working_hours(self):
        """Check for waiting hours for machines"""
        if self.is_within_work_hours():
            return self.env.timeout(0)
        else:
            current_time = convert_to_real_time(self.sim_start_time, self.env.now)
            if current_time.hour >= 16:
                next_work_start = (current_time + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
            else:
                next_work_start = current_time.replace(hour=8, minute=0, second=0, microsecond=0)

            time_to_wait = (next_work_start - current_time).total_seconds() / 60
            return self.env.timeout(time_to_wait)

    def wait_working_hours2(self, actor_ref):
        """Check for waiting hours for actors"""
        current_time = convert_to_real_time(self.sim_start_time, self.env.now)
        work_start = current_time.replace(hour=8, minute=0, second=0, microsecond=0)

        if actor_ref in self.half_day:
            work_end = current_time.replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            work_end = current_time.replace(hour=16, minute=0, second=0, microsecond=0)

        if current_time < work_start:
            return (work_start - current_time).total_seconds() / 60

        elif current_time > work_end:
            next_work_start = work_start + timedelta(days=1)
            return (next_work_start - current_time).total_seconds() / 60

        else:
            return 0

    def is_within_work_hours(self):
        real_time = convert_to_real_time(self.sim_start_time, self.env.now)
        work_start = real_time.replace(hour=8, minute=0, second=0, microsecond=0)
        work_end = real_time.replace(hour=16, minute=0, second=0, microsecond=0)
        return work_start <= real_time <= work_end

    def log(self, case, activity, start_time, finish_time, actor_ref, parent_case=None, turnaround_time=None, ):
        """Method to log events"""
        self.log_entries.append({
            "case_ID": case.id,
            "token_ID": case.token_id,
            "Activity": activity,
            "Type": case.type,
            "Specimen_typ": (parent_case.specimen_type
                             if parent_case is not None
                             else case.specimen_type),

            "Specimen_containers": case.specimen_containers,
            "Start_Time": convert_to_real_time(self.sim_start_time, start_time),
            "Finish_Time": convert_to_real_time(self.sim_start_time, finish_time),
            "Actor_ref": actor_ref,
            'Turnaround_time': turnaround_time
        })

    def sample_duration(self, actor_ref, stage_name):

        return get_sampled_duration(actor_ref, stage_name)

    def get_full_batch(self, queue, batch_size, polling_interval=1):
        """
        Gets full batch from cases from queue
        """
        while len(queue.items) < batch_size:
            yield self.env.timeout(polling_interval)
        batch = []
        for _ in range(batch_size):
            case = yield queue.get()
            batch.append(case)
        return batch
