import os

import psycopg


def test_api_database_connection_can_execute_query():
    with psycopg.connect(
        dbname=os.environ["API_DB"],
        user=os.environ["API_DB_USERNAME"],
        password=os.environ["API_DB_PASSWORD"],
        host=os.environ["API_DB_HOST"],
        port=int(os.environ["API_DB_PORT"]),
    ) as connection:
        result = connection.execute("SELECT 1").fetchone()

    assert result == (1,)
