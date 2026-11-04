import pandas as pd
from psycopg import sql

from app.db.db_connector import get_dbconnector


def read_table_from_postgres(
    db_name: str, table_name: str, columns: list[str]
) -> pd.DataFrame:
    """Read the selected columns from a PostgreSQL table into a DataFrame."""
    if not table_name:
        raise ValueError("table_name must not be empty")
    if not columns:
        raise ValueError("columns must contain at least one column name")
    if any(not isinstance(column, str) or not column for column in columns):
        raise ValueError("columns must contain non-empty column names")

    query = sql.SQL("SELECT {} FROM {}").format(
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.Identifier(table_name),
    )
    connector = get_dbconnector()
    connector.connect(db_name)
    cursor = connector.connections[db_name]["cursor"]
    cursor.execute(query)
    rows = cursor.fetchall()
    result_columns = [description.name for description in cursor.description]
    return pd.DataFrame(rows, columns=result_columns)


def get_max_id(db_name: str, table_name: str, column_name: str) -> int:
    """Return the largest integer value in the specified table column.

    Returns ``0`` when the table contains no non-null values in the column.
    """
    if not table_name:
        raise ValueError("table_name must not be empty")
    if not column_name:
        raise ValueError("column_name must not be empty")

    query = sql.SQL("SELECT COALESCE(MAX({}), 0) FROM {}").format(
        sql.Identifier(column_name),
        sql.Identifier(table_name),
    )
    connector = get_dbconnector()
    connector.connect(db_name)
    cursor = connector.connections[db_name]["cursor"]
    cursor.execute(query)
    result = cursor.fetchone()
    return int(result[0])


def table_has_records(db_name: str, table_name: str) -> bool:
    """Return whether the specified PostgreSQL table contains any records."""
    if not table_name:
        raise ValueError("table_name must not be empty")

    query = sql.SQL("SELECT EXISTS (SELECT 1 FROM {})").format(
        sql.Identifier(table_name),
    )
    connector = get_dbconnector()
    connector.connect(db_name)
    cursor = connector.connections[db_name]["cursor"]
    cursor.execute(query)
    result = cursor.fetchone()
    return bool(result[0])
