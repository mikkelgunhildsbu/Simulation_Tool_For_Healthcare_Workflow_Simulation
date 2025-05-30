import random
import simpy

from stages.base_stage import BaseStage

class AutomaticStainingStage(BaseStage):
    """
       Class to represent the automatic staining stage
       Batch size set to 25
       10% of batch sent to manual staining queue
    """

    def __init__(self, env, queues, resources, sim_start_time, log_entries, g):
        super().__init__(env, queues, resources, sim_start_time, log_entries, g)
        self.batch_staining_size = 25
        self.batch_lock2 = simpy.Resource(env, capacity=1)

    def run(self):
        while True:
            with self.batch_lock2.request() as lock_req:
                yield lock_req

                if not self.is_within_work_hours():
                    yield self.wait_working_hours()
                    continue

                batch = yield from self.get_full_batch(
                    self.queues["staining_queue"],
                    self.batch_staining_size
                )

            manual_slides = []
            automatic_slides = []

            for slide in batch:
                if random.random() < 0.10:
                    self.queues['manual_staining_queue'].put(slide)
                    manual_slides.append(slide)
                else:
                    automatic_slides.append(slide)

            if automatic_slides:
                with self.resources["staining_machine"].request() as req:
                    yield self.wait_working_hours()
                    yield req

                    start_time = self.env.now
                    yield self.env.timeout(self.g.service_automaticStaining)
                    yield self.env.timeout(random.uniform(0.1, 10))
                    finish_time = self.env.now

                    for slide in automatic_slides:
                        self.log(
                            slide,
                            "automaticStaining",
                            start_time,
                            finish_time,
                            actor_ref="Staining Machine",
                            parent_case=slide.parent_case
                        )
                        self.queues["scanning_queue"].put(slide)
