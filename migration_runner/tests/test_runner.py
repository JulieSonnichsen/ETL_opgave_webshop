from unittest.mock import MagicMock, patch

import pytest

from app.runner import _load_migrations, run_migrations


def test_load_migrations_sorts_by_numeric_version(tmp_path):
    (tmp_path / "010_add_gpu.sql").write_text("SELECT 10;", encoding="utf-8")
    (tmp_path / "2_add_ram.sql").write_text("SELECT 2;", encoding="utf-8")

    migrations = _load_migrations(tmp_path)

    assert [(version, path.name) for version, path in migrations] == [
        (2, "2_add_ram.sql"),
        (10, "010_add_gpu.sql"),
    ]


def test_load_migrations_rejects_duplicate_versions(tmp_path):
    (tmp_path / "001_create_products.sql").write_text("", encoding="utf-8")
    (tmp_path / "1_add_price.sql").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate migration version 1"):
        _load_migrations(tmp_path)


def test_load_migrations_rejects_non_numbered_sql_files(tmp_path):
    (tmp_path / "create_products.sql").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="must start with a number"):
        _load_migrations(tmp_path)


def test_run_migrations_loads_config_and_applies_pending_versions(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.runner.MIGRATIONS_ROOT", tmp_path)
    monkeypatch.setenv("DB_HOST", "db-host")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_USER", "admin")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    config_folder = tmp_path / "db_config"
    config_folder.mkdir()
    monkeypatch.setattr("app.runner.DB_CONFIG_ROOT", config_folder)
    (config_folder / "products.yml").write_text(
        "host: ${DB_HOST}\n"
        "port: ${DB_PORT}\n"
        "username: ${DB_USER}\n"
        "password: ${DB_PASSWORD}\n",
        encoding="utf-8",
    )
    migration_folder = tmp_path / "scripts" / "products"
    migration_folder.mkdir(parents=True)
    (migration_folder / "002_add_name.sql").write_text(
        "ALTER TABLE products ADD COLUMN name TEXT;", encoding="utf-8"
    )
    (migration_folder / "001_initial.sql").write_text(
        "CREATE TABLE products ();", encoding="utf-8"
    )
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = (1,)

    with patch("app.runner.psycopg.connect", return_value=connection) as connect:
        latest_version = run_migrations("products")

    assert latest_version == 2
    connect.assert_called_once_with(
        host="db-host",
        port=5432,
        dbname="products",
        user="admin",
        password="secret",
    )
    executed_sql = [
        call.args[0]
        for call in cursor.execute.call_args_list
        if call.args and isinstance(call.args[0], str)
    ]
    assert "CREATE TABLE products ();" not in executed_sql
    assert "ALTER TABLE products ADD COLUMN name TEXT;" in executed_sql
    assert ("UPDATE schema_migrations SET version = %s WHERE id = 1", (2,)) in [
        call.args for call in cursor.execute.call_args_list
    ]


def test_load_database_config_rejects_missing_environment_variable(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("app.runner.MIGRATIONS_ROOT", tmp_path)
    config_folder = tmp_path / "db_config"
    config_folder.mkdir()
    monkeypatch.setattr("app.runner.DB_CONFIG_ROOT", config_folder)
    (config_folder / "products.yml").write_text(
        "host: ${UNSET_DB_HOST}\n"
        "port: 5432\n"
        "username: admin\n"
        "password: secret\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="UNSET_DB_HOST"):
        run_migrations("products")
