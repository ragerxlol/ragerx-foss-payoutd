from math import floor

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from .constants import *
from . import log

conn = None
cur = None

def db_time_to_walltime(db_time):
    return floor(db_time + 1262304000)

def walltime_to_db_time(walltime):
    return floor(walltime - 1262304000)

def connection_init():
    """Create database connection"""

    global conn, cur

    try:
        conn = psycopg2.connect(user=PSQL_USERNAME,
                                password=PSQL_PASSWORD,
                                dbname=PSQL_NAME,
                                host=PSQL_HOST,
                                port=PSQL_PORT)
        log.message('Database connection created')
    except:
        log.error('Failed to create database connection')
        return False

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        cur = conn.cursor()
        log.message('Database cursor created')
    except:
        log.error('Failed to create database cursor')
        return False

    return True

def check_connection():
    try:
        execute('SELECT 1')
        return True
    except:
        return False

def get_connection():
    return conn, cur

def execute(query, parameters=None):
    return cur.execute(query, parameters)

def fetchone():
    return cur.fetchone()

def fetchall():
    return cur.fetchall()

def close_connection():
    """Destroy database connection"""

    global conn, cur

    if cur:
        cur.close()
        log.message('Database cursor closed')

    if conn:
        conn.close()
        log.message('Database connection closed')
