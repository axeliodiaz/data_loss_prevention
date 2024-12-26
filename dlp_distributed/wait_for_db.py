import time
import pymysql
from django.db import connections
from django.db.utils import OperationalError

MAX_RETRIES = 5
RETRY_DELAY = 5


def wait_for_db():
    print("Waiting for the database to be ready...")
    for i in range(MAX_RETRIES):
        try:
            db_conn = connections["default"]
            db_conn.cursor().execute("SELECT 1")
            print("Database is ready!")
            return
        except (OperationalError, pymysql.err.OperationalError):
            print(f"Database is not ready yet. Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

    raise Exception("Database is not ready after multiple retries.")
