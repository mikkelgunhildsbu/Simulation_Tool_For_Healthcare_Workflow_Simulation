import random
import simpy
from stages.base_stage import BaseStage


class EmbeddingStage(BaseStage):
    """
       A class to represent the automatic embedding stage
       Batch size set to 25
       24% chance a block in the block is sent to manual embedding queue
    """
    def __init__(self, env, queues, resources, sim_start_time, log_entries, g):
        super().__init__(env, queues, resources, sim_start_time, log_entries, g)
        self.batch_staining_size = 25
        self.batch_lock10 = simpy.Resource(env, capacity=1)

    def run(self):
        while True:
            with self.batch_lock10.request() as lock_req:
                yield lock_req

                if not self.is_within_work_hours():
                    yield self.wait_working_hours()
                    continue

                batch = yield from self.get_full_batch(
                    self.queues["embedding_queue"],
                    self.batch_staining_size
                )

            manual_blocks = []
            automatic_blocks = []

            for block in batch:
                if random.random() < 0.24:
                    self.queues['manual_embedding_queue'].put(block)
                    manual_blocks.append(block)
                else:
                    automatic_blocks.append(block)

            if automatic_blocks:
                with self.resources["automatic_embedding_machine"].request() as req:
                    yield self.wait_working_hours()
                    yield req

                    start_time = self.env.now
                    yield self.env.timeout(random.uniform(0.1, 30))
                    yield self.env.timeout(self.g.service_automaticEmbedding)
                    finish_time = self.env.now

                    for block in automatic_blocks:
                        self.log(
                            block,
                            "automaticEmbedding",
                            start_time,
                            finish_time,
                            actor_ref="Embedding Machine",
                            parent_case=block.parent_case
                        )
                        self.queues["manual_sectioning_queue"].put(block)
