from scipy import stats

from stages.base_stage import BaseStage

class StainingIHCStage(BaseStage):
    def __init__(self, env, queues, resources, sim_start_time, log_entries, g):
        super().__init__(env, queues, resources, sim_start_time, log_entries, g)
        self.batch_stainingIHC_size = 25

    def run(self):
        while True:
            batch = yield from self.get_full_batch (self.queues["stainingIHC_queue"], self.batch_stainingIHC_size)
            with self.resources["stainingIHC_machine"].request() as req:
                yield self.wait_working_hours()
                yield req
                start_time = self.env.now
                yield self.env.timeout(60)
                finish_time = self.env.now
            for slide in batch:
                self.log(slide, "stainingIHC", start_time, finish_time, actor_ref="StainingIHC Machine", parent_case= slide.parent_case)
                self.queues["scanning_queue"].put(slide)
