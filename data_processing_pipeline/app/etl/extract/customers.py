import pandas as pd
from psycopg import sql
from datetime import datetime

from app.db.db_connector import get_dbconnector


def get_customers_with_address(
    db_name: str,
    customer_table_name: str,
    order_table_name: str,
    num_customers: int,
    latest_order_data: datetime | None = None,
    latest_order_date: datetime | None = None,
) -> pd.DataFrame:
    """Return up to ``num_customers`` eligible customers with latest addresses.

    Customers whose latest order is after ``latest_order_data`` are excluded.
    Customers without orders are included with a null address. Latest orders
    are determined by ``order_date``, with ``order_id`` breaking date ties.
    """
    if latest_order_data is None:
        latest_order_data = latest_order_date
    if latest_order_data is None:
        raise TypeError("latest_order_data must be provided")
    if not customer_table_name or not order_table_name:
        raise ValueError("Customer and order table names must not be empty")
    if num_customers < 0:
        raise ValueError("num_customers must not be negative")

    query = sql.SQL(
        """
        SELECT customers.*, latest_order.address
        FROM {} AS customers
        LEFT JOIN LATERAL (
            SELECT orders.address, orders.order_date
            FROM {} AS orders
            WHERE orders.customer_id = customers.customer_id
            ORDER BY orders.order_date DESC NULLS LAST, orders.order_id DESC
            LIMIT 1
        ) AS latest_order ON TRUE
        WHERE latest_order.order_date <= %s
            OR latest_order.order_date IS NULL
        ORDER BY customers.customer_id
        LIMIT %s
        """
    ).format(
        sql.Identifier(customer_table_name),
        sql.Identifier(order_table_name),
    )

    connector = get_dbconnector()
    connector.connect(db_name)
    cursor = connector.connections[db_name]["cursor"]
    cursor.execute(query, (latest_order_data, num_customers))
    rows = cursor.fetchall()
    columns = [description.name for description in cursor.description]
    return pd.DataFrame(rows, columns=columns)