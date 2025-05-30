import simpy


def create_resources(env, g):
    """
    Creating all resource from globalParameters
    :param env:
    :param g: Global Parameters
    :return: all nurses (technicans), and different type of machines
    """
    nurses = {nurse: simpy.Resource(env, capacity=1)
              for nurse in (g.accessioning_nurses + g.grossing_nurses + g.decalcination_nurses +
                            g.manualEmbedding_nurses + g.manualSectioning_nurses + g.manualStaining_nurses +
                            g.finalReportFinished_nurses + g.accessioning_nurses_half + g.manualSectioning_nurses_half + g.grossing_nurses +
                            g.manualEmbedding_nurses_half + g.decalcination_nurses_half + g.manualStaining_nurses_half + g.finalReportFinished_nurses_half + g.grossing_nurses_half)}

    processing_machine = simpy.Resource(env, capacity=max(1,
                                                          g.num_processing_machines)) if g.num_processing_machines > 0 else None
    scanning_machine = simpy.Resource(env,
                                      capacity=max(1, g.num_scanning_machines)) if g.num_scanning_machines > 0 else None
    staining_machine = simpy.Resource(env,
                                      capacity=max(1, g.num_staining_machines)) if g.num_staining_machines > 0 else None
    stainingIHC_machine = simpy.Resource(env, capacity=max(1,
                                                           g.num_stainingIHC_machines)) if g.num_stainingIHC_machines > 0 else None
    automatic_embedding_machine = simpy.Resource(env, capacity=max(1,
                                                                   g.num_automatic_embedding_machines)) if g.num_automatic_embedding_machines > 0 else None

    return {
        "nurses": nurses,
        "processing_machine": processing_machine,
        "scanning_machine": scanning_machine,
        "staining_machine": staining_machine,
        "stainingIHC_machine": stainingIHC_machine,
        "automatic_embedding_machine": automatic_embedding_machine
    }
