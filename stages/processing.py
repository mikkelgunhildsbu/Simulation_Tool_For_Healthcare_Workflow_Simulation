import simpy
from stages.base_stage import BaseStage

class ProcessingStage(BaseStage):
    """
    A class to represent the processing stage
    Batch size set to 125
    """

    def __init__(self, env, queues, resources, sim_start_time, log_entries, g):
        super().__init__(env, queues, resources, sim_start_time, log_entries, g)
        self.batch_size = 125
        self.batch_lock = simpy.Resource(env, capacity=1)

    def run(self):
        while True:
            if not self.is_within_work_hours():
                yield self.wait_working_hours()

            with self.batch_lock.request() as lock_req:
                yield lock_req
                batch = yield from self.get_full_batch(self.queues["processing_queue"],
                                                       self.batch_size)

            with self.resources["processing_machine"].request() as req:
                yield req
                start = self.env.now
                yield self.env.timeout(self.g.service_processing)
                finish = self.env.now

            for block in batch:
                self.queues["embedding_queue"].put(block)
                self.log(block, "processing", start, finish,
                            "Processing Machine", block.parent_case)