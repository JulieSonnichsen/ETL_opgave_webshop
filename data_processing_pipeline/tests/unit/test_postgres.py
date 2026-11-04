from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest
from psycopg import sql

from app.etl.extract import postgres


def _identifiers(statement):
    identifiers = []
    for part in statement.seq:
        if isinstance(part, sql.Identifier):
            identifiers.append(part.strings)
        elif isinstance(part, sql.Composed):
            identifiers.extend(_identifiers(part))
    return identifiers


def test_read_table_from_postgres_selects_requested_columns_without_closing_connection(
    monkeypatch,
):
    cursor = MagicMock()
    cursor.fetchall.return_value = [(1, "Laptop"), (2, "Tablet")]
    cursor.description = [
        SimpleNamespace(name="id"),
        SimpleNamespace(name="name"),
    ]
    connector = MagicMock()
    connector.connections = {"internal_db": {"cursor": cursor}}
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    result = postgres.read_table_from_postgres(
        "internal_db", "products", ["id", "name"]
    )

    statement = cursor.execute.call_args.args[0]
    assert isinstance(statement, sql.Composed)
    assert _identifiers(statement) == [("id",), ("name",), ("products",)]
    cursor.execute.assert_called_once_with(statement)
    connector.connect.assert_called_once_with("internal_db")
    connector.close_connection.assert_not_called()
    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame({"id": [1, 2], "name": ["Laptop", "Tablet"]}),
    )


def test_read_table_from_postgres_does_not_close_connection_when_query_fails(
    monkeypatch,
):
    cursor = MagicMock()
    cursor.execute.side_effect = RuntimeError("query failed")
    connector = MagicMock()
    connector.connections = {"internal_db": {"cursor": cursor}}
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    with pytest.raises(RuntimeError, match="query failed"):
        postgres.read_table_from_postgres("internal_db", "products", ["id"])

    connector.close_connection.assert_not_called()


def test_get_max_id_returns_integer_from_requested_table_column(monkeypatch):
    cursor = MagicMock()
    cursor.fetchone.return_value = (42,)
    connector = MagicMock()
    connector.connections = {"internal_db": {"cursor": cursor}}
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    result = postgres.get_max_id("internal_db", "orders", "order_id")

    statement = cursor.execute.call_args.args[0]
    assert _identifiers(statement) == [("order_id",), ("orders",)]
    connector.connect.assert_called_once_with("internal_db")
    assert result == 42


def test_get_max_id_returns_zero_for_empty_column(monkeypatch):
    cursor = MagicMock()
    cursor.fetchone.return_value = (0,)
    connector = MagicMock()
    connector.connections = {"internal_db": {"cursor": cursor}}
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    result = postgres.get_max_id("internal_db", "orders", "order_id")

    assert result == 0


@pytest.mark.parametrize(
    ("table_name", "column_name"),
    [("", "order_id"), ("orders", "")],
)
def test_get_max_id_rejects_empty_identifiers(
    table_name, column_name, monkeypatch
):
    connector_factory = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", connector_factory)

    with pytest.raises(ValueError):
        postgres.get_max_id("internal_db", table_name, column_name)

    connector_factory.assert_not_called()
    connector_factory.assert_not_called()

@pytest.mark.parametrize(("query_result", "expected"), [((True,), True), ((False,), False)])
def test_table_has_records_returns_whether_table_is_nonempty(
    query_result, expected, monkeypatch
):
    cursor = MagicMock()
    cursor.fetchone.return_value = query_result
    connector = MagicMock()
    connector.connections = {"internal_db": {"cursor": cursor}}
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    result = postgres.table_has_records("internal_db", "products")

    statement = cursor.execute.call_args.args[0]
    assert _identifiers(statement) == [("products",)]
    connector.connect.assert_called_once_with("internal_db")
    assert result is expected


def test_table_has_records_rejects_empty_table_name(monkeypatch):
    connector_factory = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", connector_factory)

    with pytest.raises(ValueError, match="table_name must not be empty"):
        postgres.table_has_records("internal_db", "")

    connector_factory.assert_not_called()


@pytest.mark.parametrize(
    ("table_name", "columns"),
    [
        ("", ["id"]),
        ("products", []),
        ("products", [""]),
    ],
)
def test_read_table_from_postgres_rejects_empty_identifiers(
    table_name, columns, monkeypatch
):
    connector_factory = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", connector_factory)

    with pytest.raises(ValueError):
        postgres.read_table_from_postgres("internal_db", table_name, columns)

    connector_factory.assert_not_called()
