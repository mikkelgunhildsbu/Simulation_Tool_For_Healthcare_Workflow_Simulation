import pandas as pd
from sqlalchemy import create_engine
from utilities.url import url


def get_log(current_date, start_date):
    try:
        engine = create_engine(
            url
        )
        query = f"""
            SELECT 
                c.id AS case_id,
                e.token_id,
                e.happened_at,
                en."name" AS activity,
                e.event_name,
                e.event_type,
                e.actor_ref,
                e.token_type,
                c.specimen_containers,
                st.t_code_1 || ' ' || st.p_code_1  as specimen_typ,

                SUM(CASE WHEN cp.case_profile = 5 THEN 1 ELSE 0 END) AS is_consultation
            FROM trans.cases c 
            INNER JOIN trans.events e ON c.id = e.case_id 
            INNER JOIN master.net_event_names en ON en.id = e.event_name 
            inner join "views".specimen_types st on st.id = c.specimen_type 
            LEFT JOIN trans.case_profiles cp ON c.id = cp.case_id 
            WHERE patho_division = 1
              AND lab_id IS NOT NULL
              AND e.happened_at >= '{start_date}'
              AND e.happened_at <= '{current_date}'
            GROUP BY c.id, e.token_id, e.actor_ref, en."name", e.event_name, e.happened_at, e.event_type, e.token_type, st.p_code_1, st.t_code_1
            ORDER BY e.happened_at
        """
        event_log = pd.read_sql_query(query, engine)
    except Exception as e:
        print(e)

    return event_log
