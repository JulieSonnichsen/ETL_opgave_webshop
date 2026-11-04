from unittest.mock import MagicMock

import pandas as pd
import pytest
from psycopg import sql

from app.etl.load import postgres


def _identifiers(statement):
    identifiers = []
    for part in statement.seq:
        if isinstance(part, sql.Identifier):
            identifiers.extend(part.strings)
        elif isinstance(part, sql.Composed):
            identifiers.extend(_identifiers(part))
    return identifiers


def test_load_table_queues_parameterized_rows_and_commits(monkeypatch, caplog):
    connector = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)
    caplog.set_level("INFO", logger=postgres.__name__)
    table = pd.DataFrame(
        {
            "product_id": [1, 2],
            "product_name": ["Laptop", "Tablet"],
            "optional_value": [pd.NA, 42],
        }
    )

    postgres.load_table_into_postgres("internal_db", "products", table)

    connector.connect.assert_called_once_with("internal_db")
    queued_queries = connector.add_query.call_args_list
    assert len(queued_queries) == 2
    assert all(call.args[0] == "internal_db" for call in queued_queries)
    assert all(isinstance(call.args[1], sql.Composed) for call in queued_queries)
    assert _identifiers(queued_queries[0].args[1]) == [
        "products",
        "product_id",
        "product_name",
        "optional_value",
    ]
    assert queued_queries[0].args[2] == (1, "Laptop", None)
    assert queued_queries[1].args[2] == (2, "Tablet", 42)
    connector.commit_queries.assert_called_once_with("internal_db")
    assert "Loaded 2 rows into internal_db.products" in caplog.text


def test_load_table_does_not_connect_for_empty_dataframe(monkeypatch):
    connector = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)
    table = pd.DataFrame(columns=["product_id", "product_name"])

    postgres.load_table_into_postgres("internal_db", "products", table)

    connector.connect.assert_not_called()
    connector.add_query.assert_not_called()
    connector.commit_queries.assert_not_called()


@pytest.mark.parametrize(
    ("table_name", "table", "message"),
    [
        ("", pd.DataFrame({"id": [1]}), "table_name"),
        ("products", pd.DataFrame(index=[0]), "at least one column"),
        ("products", pd.DataFrame({None: [1]}), "non-empty strings"),
    ],
)
def test_load_table_rejects_invalid_identifiers_before_connecting(
    monkeypatch, table_name, table, message
):
    connector = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    with pytest.raises(ValueError, match=message):
        postgres.load_table_into_postgres("internal_db", table_name, table)

    connector.connect.assert_not_called()


def test_load_table_propagates_commit_failure(monkeypatch):
    connector = MagicMock()
    connector.commit_queries.side_effect = RuntimeError("insert failed")
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    with pytest.raises(RuntimeError, match="insert failed"):
        postgres.load_table_into_postgres(
            "internal_db",
            "products",
            pd.DataFrame({"product_id": [1]}),
        )

    connector.commit_queries.assert_called_once_with("internal_db")


def test_update_table_queues_parameterized_updates_by_product_id(
    monkeypatch, caplog
):
    connector = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)
    caplog.set_level("INFO", logger=postgres.__name__)
    table = pd.DataFrame(
        {
            "product_id": [10, 20],
            "current_price": [899.99, 499.5],
            "optional_value": [pd.NA, "updated"],
        }
    )

    postgres.update_table_in_postgres("internal_db", "products", table)

    connector.connect.assert_called_once_with("internal_db")
    queued_updates = connector.add_query.call_args_list
    assert len(queued_updates) == 2
    assert all(call.args[0] == "internal_db" for call in queued_updates)
    assert all(isinstance(call.args[1], sql.Composed) for call in queued_updates)
    assert _identifiers(queued_updates[0].args[1]) == [
        "products",
        "current_price",
        "optional_value",
        "product_id",
    ]
    assert queued_updates[0].args[2] == (899.99, None, 10)
    assert queued_updates[1].args[2] == (499.5, "updated", 20)
    connector.commit_queries.assert_not_called()
    assert "Queued 2 updates for internal_db.products" in caplog.text


def test_update_table_does_not_connect_for_empty_dataframe(monkeypatch):
    connector = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    postgres.update_table_in_postgres(
        "internal_db",
        "products",
        pd.DataFrame(columns=["product_id", "current_price"]),
    )

    connector.connect.assert_not_called()
    connector.add_query.assert_not_called()


@pytest.mark.parametrize(
    ("table_name", "table", "message"),
    [
        ("", pd.DataFrame({"product_id": [1], "current_price": [10]}), "table_name"),
        ("products", pd.DataFrame({"current_price": [10]}), "product_id"),
        ("products", pd.DataFrame({"product_id": [1]}), "at least one column to update"),
        (
            "products",
            pd.DataFrame({"product_id": [1], None: [10]}),
            "non-empty strings",
        ),
    ],
)
def test_update_table_rejects_invalid_input_before_connecting(
    monkeypatch, table_name, table, message
):
    connector = MagicMock()
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    with pytest.raises(ValueError, match=message):
        postgres.update_table_in_postgres("internal_db", table_name, table)

    connector.connect.assert_not_called()


def test_update_table_propagates_queue_failure(monkeypatch):
    connector = MagicMock()
    connector.add_query.side_effect = RuntimeError("queue failed")
    monkeypatch.setattr(postgres, "get_dbconnector", lambda: connector)

    with pytest.raises(RuntimeError, match="queue failed"):
        postgres.update_table_in_postgres(
            "internal_db",
            "products",
            pd.DataFrame({"product_id": [1], "current_price": [10]}),
        )

    connector.add_query.assert_called_once()
