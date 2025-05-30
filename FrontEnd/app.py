import copy
import csv
import json
from datetime import datetime
from flask import Flask, request, redirect, render_template, jsonify, session
from sqlalchemy import create_engine
import simpy
import pandas as pd
from pytz import FixedOffset
from dateutil.parser import isoparse

from simSetup.queue_initializer import initialize_from_event_log
from pathology_model import PathologyModel
from global_parameters import GlobalParameters as g
from simSetup.queues import create_queues
from utilities.get_event_log import get_log

from utilities.url import url

app = Flask(__name__)
app.secret_key = 'supersecretkey'

cached_state = {"data": None, "date": None, "event_log": None, "sim_event_log": None}
initial_queue_blueprint = None
queue_after = None

# Global lists to hold results (should be cleared every run)
queue_data = []
all_results = []
run_summaries = []
actor_summaries = []
case_arrival_summaries = []
activity_summaries = []
turnaround_times = []

def extract_daily_configs_from_form(form, num_days):
    daily_configs = []

    def parse_actor_list(day, activity_key):
        key = f"{activity_key}_nurse_day_{day}"
        data = form.get(key)
        if not data:
            return [], []
        try:
            actors = json.loads(data)
            full_day = [int(a['name']) for a in actors if not a['half_day']]
            half_day = [int(a['name']) for a in actors if a['half_day']]
            return full_day, half_day
        except Exception as e:
            print(f"Error parsing actor list for {key}: {e}")
            return [], []

    for day in range(1, num_days + 1):
        config = {
            "num_staining_machines": int(form.get("num_staining_machines", 1)),
            "num_automatic_embedding_machines": int(form.get("num_automatic_embedding_machines", 1)),
            "num_stainingIHC_machines": int(form.get("num_stainingIHC_machines", 1)),
            "num_scanning_machines": int(form.get("num_scanning_machines", 1)),
            "num_processing_machines": int(form.get("num_processing_machines", 1)),
        }

        for activity_key, g_attr in [
            ('accessioning', 'accessioning_nurses'),
            ('grossing', 'grossing_nurses'),
            ('manualEmbedding', 'manualEmbedding_nurses'),
            ('manualSectioning', 'manualSectioning_nurses'),
            ('decalcination', 'decalcination_nurses'),
            ('manualStaining', 'manualStaining_nurses'),
            ('finalReportFinished', 'finalReportFinished_nurses'),
        ]:
            full, half = parse_actor_list(day, activity_key)
            config[g_attr] = full
            config[f"{g_attr}_half"] = half

        daily_configs.append(config)

    return daily_configs

def load_nurse_options(csv_filename='masterSim/Sim/actorDurations/actor_dis1.csv'):
    options = {}
    with open(csv_filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            activity = row['activity'].strip().lower()
            actor = round(float(row['actor_ref'].strip()))
            options.setdefault(activity, set()).add(actor)
    for act in options:
        try:
            options[act] = sorted(options[act], key=lambda x: int(x))
        except ValueError:
            options[act] = sorted(options[act])
    return options

def run_day(start_time, carry_in_queue=None):
    env = simpy.Environment()
    queues = create_queues(env)
    if carry_in_queue:
        for qn, items in carry_in_queue.items():
            for it in items:
                queues[qn].put(copy.deepcopy(it))

    pm = PathologyModel(
        run_number=0,
        sim_start_time=start_time,
        queues=queues,
        env=env
    )
    pm.run()

    logs = [pm.results_df]
    carry_q = {qn: list(store.items) for qn, store in pm.queue_afters.items()}
    queue_lengths = pm.queue_after
    return carry_q, logs, queue_lengths

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        g.sim_days = int(request.form.get('sim_days', g.sim_days))
        g.number_of_runs = int(request.form.get('number_of_runs', g.number_of_runs))

        g.num_staining_machines = int(request.form.get('num_staining_machines', g.num_staining_machines))
        g.num_automatic_embedding_machines = int(request.form.get('num_automatic_embedding_machines', g.num_automatic_embedding_machines))
        g.num_stainingIHC_machines = int(request.form.get('num_stainingIHC_machines', g.num_stainingIHC_machines))
        g.num_scanning_machines = int(request.form.get('num_scanning_machines', g.num_scanning_machines))
        g.num_processing_machines = int(request.form.get('num_processing_machines', g.num_processing_machines))

        daily_configs = extract_daily_configs_from_form(request.form, g.sim_days)
        session['daily_configs'] = json.dumps(daily_configs)

        return redirect('/')

    nurse_options = load_nurse_options('../masterSim/Sim/actorDurations/actor_dis1.csv')
    return render_template('index.html', parameters=g, nurse_options=nurse_options)

@app.route('/run_simulation')
def run_simulation(run_start_time=None, queue=None, event_log=None):
    global initial_queue_blueprint

    if initial_queue_blueprint is None:
        return jsonify({"error": "Queue blueprint not initialized. Please run /initialize_state first."}), 400

    if queue is None:
        queue = initial_queue_blueprint

    start_time = isoparse(run_start_time) if run_start_time else sim_start_time

    for lst in [queue_data, all_results, run_summaries, actor_summaries,
                case_arrival_summaries, activity_summaries, turnaround_times]:
        lst.clear()

    try:
        daily_configs = json.loads(session.get('daily_configs', '[]'))
    except Exception as e:
        return jsonify({"error": f"Could not parse daily configs: {e}"}), 400

    num_days = len(daily_configs)
    last_queue_after = None

    for run_id in range(g.number_of_runs):
        carry_queue = initial_queue_blueprint
        for day_offset in range(num_days):
            day_start = sim_start_time + pd.Timedelta(days=day_offset)
            cfg = daily_configs[day_offset]
            carry_queue, logs, lengths = run_day(day_start, cfg, carry_queue)

            for log in logs:
                all_results.append(log)

            queue_data.append(lengths)

    return "Simulation run complete"

@app.route('/initialize_state')
def initialize_state():
    global event_log, initial_queue_blueprint, sim_start_time
    now = datetime.now(FixedOffset(120))
    current_date = now.replace(hour=8, minute=0).strftime('%Y-%m-%d %H:%M:%S') + "+2"

    event_log = get_log(current_date=current_date, start_date= current_date - pd.DateOffset(weeks= 4))
    temp_env = simpy.Environment()
    queues = create_queues(temp_env)
    sim_start_time = initialize_from_event_log(event_log, queues)
    queue_length = {queue_name: len(store.items) for queue_name, store in queues.items()}
    initial_queue_blueprint = {queue_name: list(store.items) for queue_name, store in queues.items()}

    return jsonify({"queue_state": queue_length})


if __name__ == '__main__':
    app.run(debug=True)
