class GlobalParameters:
    """
    A class to hold all global parameters and settings for the simulation.
    """

    # Machine Service Times
    service_processing = 12 * 60
    service_automaticStaining = 60
    service_scanning = 15
    service_automaticEmbedding = 25

    sim_days = 1
    sim_duration = 23.5 * 60
    number_of_runs = 3

    # Technical parameters
    accessioning_nurses = [5, 14]
    grossing_nurses = [3, 23]
    decalcination_nurses = [3]
    manualEmbedding_nurses = []
    manualSectioning_nurses = [313, 364, ]
    manualStaining_nurses = []
    finalReportFinished_nurses = [2]

    accessioning_nurses_half = []
    grossing_nurses_half = []
    decalcination_nurses_half = []
    manualSectioning_nurses_half = []
    manualEmbedding_nurses_half = [291]
    manualStaining_nurses_half = []
    finalReportFinished_nurses_half = [1000]

    # Machine Parameters
    num_processing_machines = 1
    num_scanning_machines = 6
    num_staining_machines = 6
    num_stainingIHC_machines = 2
    num_automatic_embedding_machines = 2
