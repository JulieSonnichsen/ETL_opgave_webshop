from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
from datetime import datetime

from app.etl.extract import customers


def test_get_customers_with_address_filters_by_latest_order_and_limits_results(
    monkeypatch,
):
    cursor = MagicMock()
    cursor.fetchall.return_value = [
        (1, "Alice", "Main Street"),
        (2, "Bob", None),
    ]
    cursor.description = [
        SimpleNamespace(name="customer_id"),
        SimpleNamespace(name="customer_name"),
        SimpleNamespace(name="address"),
    ]
    connector = MagicMock()
    connector.connections = {"internal_db": {"cursor": cursor}}
    monkeypatch.setattr(customers, "get_dbconnector", lambda: connector)

    result = customers.get_customers_with_address(
        "internal_db",
        "customers",
        "orders",
        num_customers=2,
        latest_order_data=datetime(2025, 1, 1),
    )

    statement = cursor.execute.call_args.args[0].as_string()
    assert "LEFT JOIN LATERAL" in statement
    assert "ORDER BY orders.order_date DESC NULLS LAST, orders.order_id DESC" in statement
    assert "LIMIT 1" in statement
    assert "WHERE latest_order.order_date <= %s" in statement
    assert "ORDER BY customers.customer_id" in statement
    assert statement.rstrip().endswith("LIMIT %s")
    assert cursor.execute.call_args.args[1] == (datetime(2025, 1, 1), 2)
    assert '"customers"' in statement
    assert '"orders"' in statement
    connector.connect.assert_called_once_with("internal_db")
    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame(
            {
                "customer_id": [1, 2],
                "customer_name": ["Alice", "Bob"],
                "address": ["Main Street", None],
            }
        ),
    )


def test_get_customers_with_address_rejects_empty_table_names(monkeypatch):
    connector_factory = MagicMock()
    monkeypatch.setattr(customers, "get_dbconnector", connector_factory)

    with pytest.raises(ValueError, match="must not be empty"):
        customers.get_customers_with_address(
            "internal_db",
            customer_table_name="",
            order_table_name="orders",
            num_customers=1,
            latest_order_data=datetime(2025, 1, 1),
        )

    connector_factory.assert_not_called()


def test_get_customers_with_address_rejects_negative_customer_count(monkeypatch):
    connector_factory = MagicMock()
    monkeypatch.setattr(customers, "get_dbconnector", connector_factory)

    with pytest.raises(ValueError, match="num_customers must not be negative"):
        customers.get_customers_with_address(
            "internal_db",
            customer_table_name="customers",
            order_table_name="orders",
            num_customers=-1,
            latest_order_data=datetime(2025, 1, 1),
        )

    connector_factory.assert_not_called()
