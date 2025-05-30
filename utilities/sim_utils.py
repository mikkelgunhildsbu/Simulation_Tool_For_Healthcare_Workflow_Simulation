from datetime import timedelta


def convert_to_real_time(sim_start_time, sim_time_minutes):
    return sim_start_time + timedelta(minutes=sim_time_minutes)


def is_within_working_hours(sim_start_time, sim_time):
    real_time = convert_to_real_time(sim_start_time, sim_time)
    work_start = real_time.replace(hour=8, minute=0, second=0, microsecond=0)
    work_end = real_time.replace(hour=16, minute=0, second=0, microsecond=0)
    return work_start <= real_time <= work_end
