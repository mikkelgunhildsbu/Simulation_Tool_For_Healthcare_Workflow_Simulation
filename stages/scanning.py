import random
import simpy
from stages.base_stage import BaseStage
from entities import SlideEntity

class ScanningStage(BaseStage):
    """
    Case to represent scanning stage
    Batch size of 25
    Checks all slides of a case is scanned before sending case to next stage
    """
    def __init__(self, env, queues, resources, sim_start_time, log_entries, g):
        super().__init__(env, queues, resources, sim_start_time, log_entries, g)
        self.batch_scanning_size = 25
        self.batch_lock = simpy.Resource(env, capacity=1)

    def run(self):
        while True:
            with self.batch_lock.request() as lock_req:
                yield lock_req

                if not self.is_within_work_hours():
                    yield self.wait_working_hours()
                    continue

                batch = yield from self.get_full_batch(self.queues["scanning_queue"],
                                                       self.batch_scanning_size)

            with self.resources["scanning_machine"].request() as req:
                yield self.wait_working_hours()
                yield req
                start_time = self.env.now
                yield self.env.timeout(random.uniform(0.1,10))
                yield self.env.timeout(self.g.service_scanning)
                finish_time = self.env.now

            cases = []
            for slide in batch:
                self.log(slide, "scanning", start_time, finish_time, "Scanning Machine", slide.parent_case)

                case = slide.parent_case
                case.scanned_slides += 1

                if (not case._sent_to_final) and case.scanned_slides == len(case.slides) and case.id not in cases:
                    cases.append(case.id)
                    case.token_id = case.id
                    self.queues["final_report_queue"].put(case)
                    case._sent_to_final = True