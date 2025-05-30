import random

import pandas as pd

from entities import CaseEntity, BlockEntity
from stages.base_stage import BaseStage
from utilities.stage_utilites import checkRework
from utilities.sim_utils import convert_to_real_time


class FinalReportFinishedStage(BaseStage):
    """
    Class to represent MicroscopicAnalysis
    Static service time of 45 minutes
    Calls rework logic to determine which outcome of rework is necessary
    If a case is sent to rework which does not have a block (due to state initializer) create a block for each slide
    """
    def run(self, actor):
        while True:
            case = yield self.queues["final_report_queue"].get()
            with self.resources["nurses"][actor].request() as req:
                yield self.env.timeout(self.wait_working_hours2(actor))
                yield req

                start_time = self.env.now
                yield self.env.timeout(45)
                finish_time = self.env.now

                self.log(case, "microscopicAnalysis", start_time, finish_time, actor, parent_case=None,
                         turnaround_time=None)

                event = checkRework(case.specimen_type)
                if event == 99:
                    case.finish_time = convert_to_real_time(self.sim_start_time, finish_time)
                    if pd.isna(case.start_time):
                        turnaround_hours = pd.NA
                    else:
                        delta = case.finish_time - case.start_time
                        turnaround_hours = delta / pd.Timedelta(hours=1)
                    self.log(case, "finalReportFinished", finish_time, finish_time, actor, parent_case= None , turnaround_time=turnaround_hours)

                elif event in (91, 92):
                    if not case.blocks:
                        if not case.slides:
                            BlockEntity(case)
                        else:
                            for slide in case.slides:
                                block = BlockEntity(case)
                                slide.parent_block = block
                                block.type = 2
                    for block in case.blocks:
                        if event == 91:
                            block.parent_case.stainingIHC = True
                            self.log(block, "ihcRequested", finish_time, finish_time, actor)
                            self.queues["manual_sectioning_queue"].put(block)
                            case._sent_to_final = False

                        else:
                            block.parent_case.stainingIHC = False
                            self.log(block, "specialStainRequested", finish_time, finish_time, actor)
                            self.queues["manual_sectioning_queue"].put(block)
                            case._sent_to_final = False


                elif event == 93:
                    self.log(case, "additionalGrossingRequested", start_time, finish_time, actor)
                    self.queues["grossing_queue"].put(case)
                    case._sent_to_final = False






