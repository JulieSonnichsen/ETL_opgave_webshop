import logging

import pandas as pd
from psycopg import sql

from app.db.db_connector import get_dbconnector


logger = logging.getLogger(__name__)


def load_table_into_postgres(
    db_name: str,
    table_name: str,
    table: pd.DataFrame,
) -> None:
    """Insert all rows from a DataFrame into a PostgreSQL table atomically."""
    if not table_name:
        raise ValueError("table_name must not be empty")
    if len(table.columns) == 0:
        raise ValueError("table must contain at least one column")
    if any(not isinstance(column, str) or not column for column in table.columns):
        raise ValueError("table columns must be non-empty strings")
    if table.empty:
        logger.info("Skipping empty load for %s.%s", db_name, table_name)
        return

    insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(sql.Identifier(column) for column in table.columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in table.columns),
    )
    rows = (
        tuple(row)
        for row in table.astype(object).where(pd.notna(table), None).itertuples(
            index=False,
            name=None,
        )
    )

    connector = get_dbconnector()
    connector.connect(db_name)
    for row in rows:
        connector.add_query(db_name, insert_query, row)
    connector.commit_queries(db_name)
    logger.info("Loaded %d rows into %s.%s", len(table), db_name, table_name)

def update_table_in_postgres(db_name: str, table_name: str, table: pd.DataFrame) -> None:
    """Queue updates for rows identified by ``product_id``.

    All columns other than ``product_id`` are written to the matching row.
    Updates are queued rather than committed so callers can include them in
    the same transaction as related inserts.
    """
    if not table_name:
        raise ValueError("table_name must not be empty")
    if len(table.columns) == 0:
        raise ValueError("table must contain at least one column")
    if any(not isinstance(column, str) or not column for column in table.columns):
        raise ValueError("table columns must be non-empty strings")
    if "product_id" not in table.columns:
        raise ValueError("table must contain a 'product_id' column")

    update_columns = [column for column in table.columns if column != "product_id"]
    if not update_columns:
        raise ValueError("table must contain at least one column to update")
    if table.empty:
        logger.info("Skipping empty update for %s.%s", db_name, table_name)
        return

    update_query = sql.SQL("UPDATE {} SET {} WHERE {} = {}").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(column), sql.Placeholder())
            for column in update_columns
        ),
        sql.Identifier("product_id"),
        sql.Placeholder(),
    )
    rows = table.astype(object).where(pd.notna(table), None)

    connector = get_dbconnector()
    connector.connect(db_name)
    for row in rows.loc[:, update_columns + ["product_id"]].itertuples(
        index=False,
        name=None,
    ):
        connector.add_query(db_name, update_query, tuple(row))
    logger.info("Queued %d updates for %s.%s", len(table), db_name, table_name)