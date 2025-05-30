import random

from scipy import stats

from stages.base_stage import BaseStage
from entities import SlideEntity


class ManualSectioningStage(BaseStage):
    """
    Class to represent the manual sectioning stage.
    - Normal process
    - Blocks turn into slides before sending to the next queue
    - If stainingIHC is requested send to that queue
    """
    def run(self, actor):
        while True:
            block = yield self.queues["manual_sectioning_queue"].get()
            with self.resources["nurses"][actor].request() as req:
                yield self.env.timeout(self.wait_working_hours2(actor))
                yield req
                start_time = self.env.now
                duration = self.sample_duration(actor, "manualSectioning")
                yield self.env.timeout(duration)
                finish_time = self.env.now
                self.log(block, "manualSectioning", start_time, finish_time, actor, block.parent_case)

            slide = SlideEntity(block.parent_case, block)

            slide.stainingIHC = block.stainingIHC

            if slide.parent_case.stainingIHC:
                self.queues["stainingIHC_queue"].put(slide)
            else:
                self.queues["staining_queue"].put(slide)
