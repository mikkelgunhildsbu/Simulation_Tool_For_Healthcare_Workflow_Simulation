from stages.base_stage import BaseStage

class DecalcinationStage(BaseStage):
    """
    A class to represent the Decalcination Stage
    """
    def run(self, nurse):
        while True:
            block = yield self.queues["decalcination_queue"].get()

            with self.resources["nurses"][nurse].request() as req:
                yield self.env.timeout(self.wait_working_hours2(nurse))
                yield req
                start_time = self.env.now
                duration = self.sample_duration(nurse, "decalcination")
                yield self.env.timeout(duration)
                finish_time = self.env.now

                self.log(block, "decalcination", start_time, finish_time, nurse, block.parent_case)

            self.queues["processing_queue"].put(block)
