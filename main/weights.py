from sqlalchemy import create_engine, Column, Integer, String, Date, JSON, text
from sqlalchemy.ext.declarative import declarative_base
import json
import pandas as pd
import logging


def get_json_by_record_type(db, port_n):
    # Query to retrieve JSON data by record_type
    logging.debug(f"get_json({db}, {port_n})")
    sql = text('''
        SELECT id, date, risk_mes, obj_type, int_type, weights from Trading.weights 
        WHERE port_name = :p_name
        ''')
    with db.connect() as conn:
        results = conn.execute(sql, {'p_name': port_n})

    # Convert results to a list of dictionaries
    records = []
    for result in results:
        logging.debug(result)
        record = dict()
        record['Date'] = result['date']
        record['RM'] = result['risk_mes']
        record['Objective'] = result['obj_type']
        record['Interval'] = result['int_type']
        record.update(json.loads(result['weights']))
        records.append(record)
    df = pd.DataFrame(records)
    df['Date'] = df['Date'].astype(str)
    return df
