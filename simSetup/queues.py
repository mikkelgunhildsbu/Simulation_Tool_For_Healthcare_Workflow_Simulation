import simpy


def create_queues(env):
    """
    Assigning one queue per stage
    :param env:
    :return:
    """
    return {
        "accessioning_queue": simpy.Store(env),
        "grossing_queue": simpy.FilterStore(env),
        "decalcination_queue": simpy.Store(env),
        "processing_queue": simpy.Store(env),
        "embedding_queue": simpy.Store(env),
        "manual_embedding_queue": simpy.Store(env),
        "manual_staining_queue": simpy.Store(env),
        "manual_sectioning_queue": simpy.Store(env),
        "staining_queue": simpy.Store(env),
        "stainingIHC_queue": simpy.Store(env),
        "scanning_queue": simpy.Store(env),
        "final_report_queue": simpy.Store(env)
    }
