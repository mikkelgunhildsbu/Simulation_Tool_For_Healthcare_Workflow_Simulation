# accessioning.py
from stages.base_stage import BaseStage
from utilities.sim_utils import convert_to_real_time


class AccessioningStage(BaseStage):
    """
    A class to represent the accessioning stage
    """
    def run(self, nurse):
        while True:
            case = yield self.queues["accessioning_queue"].get()
            with self.resources["nurses"][nurse].request() as req:
                yield self.env.timeout(self.wait_working_hours2(nurse))
                yield req

                start_time = self.env.now
                duration = self.sample_duration(nurse, "accessioning")
                yield self.env.timeout(duration)
                finish_time = self.env.now

                case.start_time = convert_to_real_time(self.sim_start_time, start_time)

                self.log(case, "accessioning", start_time, finish_time, nurse)

            self.queues["grossing_queue"].put(case)
