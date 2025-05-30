import random

from scipy import stats

from entities import CaseEntity, BlockEntity
from utilities.stage_utilites import num_blocks_generator
from stages.base_stage import BaseStage

class GrossingStage(BaseStage):

    """
    A class to represent the grossing stage.
    - Collects case from queue
    - Requests technical/actor
    - Waits for grossing service time
    - Calls decision tree to decide how many blocks to split into
    - Creates new blocks and send them to next queue
    """

    def run(self, nurse):
        while True:
            items = list(self.queues["grossing_queue"].items)
            if not items:
                yield self.env.timeout(1)
                continue

            chosen_case = random.choice(items)

            case = yield self.queues["grossing_queue"].get(lambda x: x == chosen_case)
            with self.resources["nurses"][nurse].request() as req:
                yield self.env.timeout(self.wait_working_hours2(nurse))
                yield req
                start_time = self.env.now
                duration = self.sample_duration(nurse, "grossing")
                yield self.env.timeout(duration)
                finish_time = self.env.now

                self.log(case, "grossing", start_time, finish_time, nurse)

            num_blocks = num_blocks_generator(case)

            for _ in range(num_blocks):
                block = BlockEntity(case)

                if random.random() < 0.01:
                    self.queues["decalcination_queue"].put(block)
                else:
                    self.queues["processing_queue"].put(block)
