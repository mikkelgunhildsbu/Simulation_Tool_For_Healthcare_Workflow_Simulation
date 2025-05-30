import simpy
import pandas as pd
from datetime import datetime

from global_parameters import GlobalParameters as g

from simSetup.resources import create_resources
from simSetup.queues import create_queues

from stages.base_stage import BaseStage
from stages.decalcination import DecalcinationStage
from stages.manualEmbedding import ManualEmbeddingStage
from stages.manualStaining import ManualStainingStage
from stages.stainingIHC import StainingIHCStage
from stages.accessioning import AccessioningStage
from stages.grossing import GrossingStage
from stages.processing import ProcessingStage
from stages.create_cases import CreateCases
from stages.embedding import EmbeddingStage
from stages.manual_sectioning_stage import ManualSectioningStage
from stages.automaticStaining import AutomaticStainingStage
from stages.scanning import ScanningStage
from stages.microscopicAnalysis import FinalReportFinishedStage

from utilities.stage_utilites import get_cases_per_day


class PathologyModel:

    def __init__(self, run_number, sim_start_time=None, queues=None, env=None):
        """
        A class to connect all simulation components and run the simulation


        :param run_number: Which run
        :param sim_start_time: The start time of the simulation
        :param queues: Queue state at the start of the simulations. If None new queues are created
        :param env: The simPy enviorment
        """

        self.env = env if env else simpy.Environment()
        self.run_number = run_number

        self.resources = create_resources(self.env, g)
        self.log_entries = []
        self.cases_today = []

        if queues is not None:
            self.queues = queues
        else:
            self.queues = create_queues(self.env)

        if sim_start_time is not None:
            self.sim_start_time = sim_start_time
        else:
            self.sim_start_time = datetime.today().replace(hour=8, minute=0, second=0, microsecond=0)


        self.base_stage = BaseStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g

        )
        self.createCases_stage = CreateCases(
            self.env, self.queues, g, self.sim_start_time
        )
        self.accessioning_stage = AccessioningStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.decalcination_stage = DecalcinationStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.grossing_stage = GrossingStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )

        self.processing_stage = ProcessingStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.embedding_stage = EmbeddingStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.manual_sectioning_stage = ManualSectioningStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.manual_staining_stage = ManualStainingStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.manual_embedding_stage = ManualEmbeddingStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.automatic_staining_stage = AutomaticStainingStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.stainingIHC_stage = StainingIHCStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.scanning_stage = ScanningStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )
        self.final_report_finished_stage = FinalReportFinishedStage(
            self.env, self.queues, self.resources, self.sim_start_time, self.log_entries, g
        )

    def run(self):
        """
        Execute the simulation by scheduling processes for each stage and running the environment.
        """
        for i in range(g.sim_days):
            self.cases_today.append(get_cases_per_day(self.sim_start_time, i))

        self.env.process(self.createCases_stage.run(self.cases_today))

        for nurse in g.accessioning_nurses + g.accessioning_nurses_half:
            self.env.process(self.accessioning_stage.run(nurse))

        for nurse in g.grossing_nurses + g.grossing_nurses_half:
            self.env.process(self.grossing_stage.run(nurse))

        for nurse in g.decalcination_nurses + g.decalcination_nurses_half:
            self.env.process(self.decalcination_stage.run(nurse))

        for nurse in g.manualEmbedding_nurses + g.manualEmbedding_nurses_half:
            self.env.process(self.manual_embedding_stage.run(nurse))

        for _ in range(g.num_processing_machines):
            self.env.process(self.processing_stage.run())

        for _ in range(g.num_automatic_embedding_machines):
            self.env.process(self.embedding_stage.run())

        for nurse in g.manualSectioning_nurses + g.manualSectioning_nurses_half:
            self.env.process(self.manual_sectioning_stage.run(nurse))

        for nurse in g.manualStaining_nurses + g.manualStaining_nurses_half:
            self.env.process(self.manual_staining_stage.run(nurse))

        for _ in range(g.num_staining_machines):
            self.env.process(self.automatic_staining_stage.run())

        for _ in range(g.num_stainingIHC_machines):
            self.env.process(self.stainingIHC_stage.run())

        for _ in range(g.num_scanning_machines):
            self.env.process(self.scanning_stage.run())

        for nurse in g.finalReportFinished_nurses + g.finalReportFinished_nurses_half:
            self.env.process(self.final_report_finished_stage.run(nurse))

        # Run the simulation until the specified simulation duration is reached

        self.env.run(until=g.sim_duration)


        self.queue_after = {queue_name: len(store.items) for queue_name, store in self.queues.items()}

        self.queue_afters = self.queues


        self.results_df = pd.DataFrame(self.log_entries)



