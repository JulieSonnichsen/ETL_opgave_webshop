from unittest.mock import MagicMock, call

import pytest

from app.db import db_connector


def test_commit_queries_executes_queue_and_commits_once():
    connector = db_connector.DBConnector()
    connection = MagicMock()
    cursor = MagicMock()
    connector.connections["api_db"] = {
        "connection": connection,
        "cursor": cursor,
        "querie_queue": [
            {"query": "INSERT INTO products VALUES (%s)", "vars": (1,)},
            {"query": "DELETE FROM products", "vars": None},
        ],
    }

    connector.commit_queries("api_db")

    assert cursor.execute.call_args_list == [
        call("INSERT INTO products VALUES (%s)", (1,)),
        call("DELETE FROM products"),
    ]
    connection.commit.assert_called_once_with()
    connection.rollback.assert_not_called()
    assert connector.connections["api_db"]["querie_queue"] == []


def test_commit_queries_commits_and_clears_an_empty_queue():
    connector = db_connector.DBConnector()
    connection = MagicMock()
    query_queue = []
    connector.connections["api_db"] = {
        "connection": connection,
        "cursor": MagicMock(),
        "querie_queue": query_queue,
    }

    connector.commit_queries("api_db")

    connection.commit.assert_called_once_with()
    connection.rollback.assert_not_called()
    assert query_queue == []


def test_commit_queries_rolls_back_and_keeps_queue_on_failure():
    connector = db_connector.DBConnector()
    connection = MagicMock()
    cursor = MagicMock()
    cursor.execute.side_effect = [None, RuntimeError("query failed")]
    query_queue = [
        {"query": "INSERT INTO products VALUES (%s)", "vars": (1,)},
        {"query": "INVALID SQL", "vars": None},
    ]
    connector.connections["api_db"] = {
        "connection": connection,
        "cursor": cursor,
        "querie_queue": query_queue,
    }

    with pytest.raises(RuntimeError, match="query failed"):
        connector.commit_queries("api_db")

    connection.commit.assert_not_called()
    connection.rollback.assert_called_once_with()
    assert connector.connections["api_db"]["querie_queue"] is query_queue


def test_commit_queries_rolls_back_and_keeps_queue_if_commit_fails():
    connector = db_connector.DBConnector()
    connection = MagicMock()
    connection.commit.side_effect = RuntimeError("commit failed")
    query_queue = [{"query": "DELETE FROM products", "vars": None}]
    connector.connections["api_db"] = {
        "connection": connection,
        "cursor": MagicMock(),
        "querie_queue": query_queue,
    }

    with pytest.raises(RuntimeError, match="commit failed"):
        connector.commit_queries("api_db")

    connection.rollback.assert_called_once_with()
    assert connector.connections["api_db"]["querie_queue"] is query_queue


def test_connect_loads_config_opens_connection_and_stores_cursor(monkeypatch):
    config = {
        "db_name": "api_db",
        "host": "database",
        "port": "5432",
        "username": "app",
        "password": "secret",
    }
    monkeypatch.setattr(db_connector, "_read_db_config", MagicMock(return_value=config))
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = cursor
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(db_connector.psycopg, "connect", connect)
    connector = db_connector.DBConnector()

    connector.connect("api_db")

    db_connector._read_db_config.assert_called_once_with(db_name="api_db")
    connect.assert_called_once_with(
        host="database",
        port="5432",
        user="app",
        password="secret",
        dbname="api_db",
    )
    connection.cursor.assert_called_once_with()
    assert connector.connections["api_db"] == {
        "connection": connection,
        "cursor": cursor,
        "querie_queue": [],
    }


def test_connect_reuses_open_connection_and_preserves_queued_queries(monkeypatch):
    connector = db_connector.DBConnector()
    connection = MagicMock()
    connection.closed = False
    config = {
        "db_name": "api_db",
        "host": "database",
        "port": "5432",
        "username": "app",
        "password": "secret",
    }
    read_config = MagicMock(return_value=config)
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr(db_connector, "_read_db_config", read_config)
    monkeypatch.setattr(db_connector.psycopg, "connect", connect)

    connector.connect("api_db")
    connector.add_query(
        "api_db",
        "INSERT INTO products VALUES (%s)",
        (1,),
    )
    query_queue = connector.connections["api_db"]["querie_queue"]

    connector.connect("api_db")
    connector.add_query(
        "api_db",
        "INSERT INTO products VALUES (%s)",
        (2,),
    )
    connector.commit_queries("api_db")

    read_config.assert_called_once_with(db_name="api_db")
    connect.assert_called_once()
    assert connection.cursor.return_value.execute.call_args_list == [
        call("INSERT INTO products VALUES (%s)", (1,)),
        call("INSERT INTO products VALUES (%s)", (2,)),
    ]
    connection.commit.assert_called_once_with()
    assert connector.connections["api_db"]["querie_queue"] is query_queue
    assert query_queue == []


def test_connect_reopens_closed_connection_without_dropping_queued_queries(
    monkeypatch,
):
    connector = db_connector.DBConnector()
    closed_connection = MagicMock()
    closed_connection.closed = True
    query_queue = [{"query": "INSERT INTO products VALUES (%s)", "vars": (1,)}]
    connector.connections["api_db"] = {
        "connection": closed_connection,
        "cursor": MagicMock(),
        "querie_queue": query_queue,
    }
    config = {
        "db_name": "api_db",
        "host": "database",
        "port": "5432",
        "username": "app",
        "password": "secret",
    }
    monkeypatch.setattr(db_connector, "_read_db_config", MagicMock(return_value=config))
    new_connection = MagicMock()
    new_connection.closed = False
    monkeypatch.setattr(
        db_connector.psycopg,
        "connect",
        MagicMock(return_value=new_connection),
    )

    connector.connect("api_db")

    assert connector.connections["api_db"]["connection"] is new_connection
    assert connector.connections["api_db"]["querie_queue"] is query_queue


def test_close_connection_closes_stored_connection():
    connector = db_connector.DBConnector()
    connection = MagicMock()
    connector.connections["api_db"] = {"connection": connection}

    connector.close_connection("api_db")

    connection.close.assert_called_once_with()


def test_add_query_appends_query_and_parameters():
    connector = db_connector.DBConnector()
    query_queue = []
    connector.connections["api_db"] = {"querie_queue": query_queue}
    parameters = (42,)

    connector.add_query(
        "api_db",
        "DELETE FROM products WHERE id = %s",
        parameters,
    )

    assert query_queue == [
        {
            "query": "DELETE FROM products WHERE id = %s",
            "vars": parameters,
        }
    ]


def test_add_query_defaults_parameters_to_none():
    connector = db_connector.DBConnector()
    connector.connections["api_db"] = {"querie_queue": []}

    connector.add_query("api_db", "DELETE FROM products")

    assert connector.connections["api_db"]["querie_queue"] == [
        {"query": "DELETE FROM products", "vars": None}
    ]


def test_get_dbconnector_returns_and_caches_singleton(monkeypatch):
    monkeypatch.setattr(db_connector, "_db", None)

    first_connector = db_connector.get_dbconnector()
    second_connector = db_connector.get_dbconnector()

    assert first_connector is second_connector
    assert isinstance(first_connector, db_connector.DBConnector)


def test_read_db_config_loads_yaml_and_resolves_environment_variables(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(db_connector, "DB_CONFIG_ROOT", tmp_path)
    monkeypatch.setenv("DB_HOST", "database")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USERNAME", "app")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    (tmp_path / "api_db.yml").write_text(
        "host: ${DB_HOST}\n"
        "port: ${DB_PORT}\n"
        "username: ${DB_USERNAME}\n"
        "password: ${DB_PASSWORD}\n",
        encoding="utf-8",
    )

    config = db_connector._read_db_config("api_db")

    assert config == {
        "db_name": "api_db",
        "host": "database",
        "port": "5432",
        "username": "app",
        "password": "secret",
    }


def test_resolve_environment_variables_replaces_nested_values(monkeypatch):
    monkeypatch.setenv("DB_HOST", "database")
    monkeypatch.setenv("DB_PORT", "5432")
    value = {
        "host": "${DB_HOST}",
        "port": "${DB_PORT}",
        "options": ["prefix-${DB_HOST}", {"enabled": True}],
        "timeout": 10,
    }

    resolved = db_connector._resolve_environment_variables(value)

    assert resolved == {
        "host": "database",
        "port": "5432",
        "options": ["prefix-database", {"enabled": True}],
        "timeout": 10,
    }


def test_read_db_config_raises_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(db_connector, "DB_CONFIG_ROOT", tmp_path)

    with pytest.raises(FileNotFoundError):
        db_connector._read_db_config("missing_db")


def test_read_db_config_rejects_unset_environment_variable(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(db_connector, "DB_CONFIG_ROOT", tmp_path)
    (tmp_path / "api_db.yml").write_text(
        "host: ${UNSET_DB_HOST}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="UNSET_DB_HOST"):
        db_connector._read_db_config("api_db")


def test_read_db_config_rejects_non_mapping_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(db_connector, "DB_CONFIG_ROOT", tmp_path)
    (tmp_path / "api_db.yml").write_text("- host\n- port\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a YAML mapping"):
        db_connector._read_db_config("api_db")


@pytest.mark.parametrize("db_name", ["", ".", "..", "../api_db", r"..\api_db"])
def test_read_db_config_rejects_paths_as_database_names(db_name):
    with pytest.raises(ValueError, match="not a path"):
        db_connector._read_db_config(db_name)
