from scipy import stats

from stages.base_stage import BaseStage


class ManualStainingStage(BaseStage):

    """
    Class to represent the manual staining stage
    """

    def run(self, nurse):
        while True:
            slide = yield self.queues["manual_staining_queue"].get()
            with self.resources["nurses"][nurse].request() as req:
                yield self.env.timeout(self.wait_working_hours2(nurse))
                yield req
                start_time = self.env.now
                yield self.env.timeout(5)
                finish_time = self.env.now
                self.log(slide, "manualStaining", start_time, finish_time, nurse, slide.parent_case)
            self.queues["scanning_queue"].put(slide)
