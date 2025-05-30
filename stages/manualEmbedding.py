from scipy import stats

from stages.base_stage import BaseStage


class ManualEmbeddingStage(BaseStage):
    """
    A class to represent the manual embedding stage
    """
    def run(self, nurse):
        while True:
            block = yield self.queues["manual_embedding_queue"].get()
            with self.resources["nurses"][nurse].request() as req:
                yield self.env.timeout(self.wait_working_hours2(nurse))
                yield req

                start_time = self.env.now
                duration = self.sample_duration(nurse, "manualEmbedding")

                yield self.env.timeout(duration)
                finish_time = self.env.now

                self.log(block, "manualEmbedding", start_time, finish_time, nurse,  block.parent_case)

            self.queues["manual_sectioning_queue"].put(block)
