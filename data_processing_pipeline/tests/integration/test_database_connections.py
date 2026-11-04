import pytest

from app.db.db_connector import DBConnector


@pytest.mark.parametrize("db_name", ["internal_db", "api_db"])
def test_database_connection_can_execute_query(db_name):
    connector = DBConnector()
    try:
        connector.connect(db_name)
        cursor = connector.connections[db_name]["cursor"]
        cursor.execute("SELECT 1")

        assert cursor.fetchone() == (1,)
    finally:
        if db_name in connector.connections:
            connector.close_connection(db_name)
