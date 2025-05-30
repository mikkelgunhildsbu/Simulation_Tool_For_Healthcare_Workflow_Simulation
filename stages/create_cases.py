from entities import CaseEntity
from utilities.sim_utils import convert_to_real_time
from utilities.stage_utilites import getSpecimenType, getSpecimenContainer


class CreateCases:
    """
    Class to generate new cases arriving at the laboratory
    specimen type and number og containers are assigned
    Case sent to accessioning queue
    """
    def __init__(self, env, queues, g, sim_start_time):
        self.env = env
        self.queues = queues
        self.g = g
        self.sim_start_time = sim_start_time
        self.last_day = -1

    def run(self, num_arrivals):

        while True:
            current_day = int(self.env.now // (24 * 60))
            if current_day != self.last_day:
                self.last_day = current_day

                for _ in range(num_arrivals[current_day]):
                    case = CaseEntity()
                    case.specimen_type = getSpecimenType()
                    case.specimen_containers = getSpecimenContainer(case.specimen_type)
                    case.token_id = case.id
                    self.queues["accessioning_queue"].put(case)

                print(
                    f"Day {current_day}: Created {num_arrivals[current_day]} new cases at {convert_to_real_time(self.sim_start_time, self.env.now)}")

            yield self.env.timeout(60)




