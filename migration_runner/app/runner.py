import os
import re
from collections.abc import Mapping
from pathlib import Path

import psycopg
import yaml


MIGRATION_TABLE = "schema_migrations"
MIGRATIONS_ROOT = Path("/migrations")
DB_CONFIG_ROOT = Path("/db_config")
_MIGRATION_FILE_PATTERN = re.compile(r"^(\d+)(?:[_-].*)?\.sql$", re.IGNORECASE)
_ENVIRONMENT_VARIABLE_PATTERN = re.compile(r"\$\{([^}]+)\}")
_MIGRATION_ADVISORY_LOCK_ID = 741852963


def _resolve_environment_variables(value: object) -> object:
    """Resolve ``${NAME}`` references recursively in YAML values."""
    if isinstance(value, str):

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            try:
                return os.environ[name]
            except KeyError as error:
                raise ValueError(
                    f"Environment variable {name!r} used in migration config "
                    "is not set"
                ) from error

        return _ENVIRONMENT_VARIABLE_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [_resolve_environment_variables(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _resolve_environment_variables(item)
            for key, item in value.items()
        }
    return value


def _load_database_config(db_name: str) -> dict[str, object]:
    """Load and validate the connection settings for a database."""
    if (
        not db_name
        or db_name in {".", ".."}
        or "/" in db_name
        or "\\" in db_name
    ):
        raise ValueError("db_name must be a database name, not a path")

    config_path = DB_CONFIG_ROOT / f"{db_name}.yml"
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    config = _resolve_environment_variables(config)
    if not isinstance(config, Mapping):
        raise ValueError(f"Database config must be a YAML mapping: {config_path}")

    settings = dict(config)
    if "username" in settings:
        if "user" in settings:
            raise ValueError(
                f"Database config cannot contain both 'user' and 'username': "
                f"{config_path}"
            )
        settings["user"] = settings.pop("username")

    required = ("host", "port", "user", "password")
    missing = [key for key in required if key not in settings]
    if missing:
        raise ValueError(
            f"Database config is missing required settings "
            f"{', '.join(missing)}: {config_path}"
        )

    settings["port"] = int(settings["port"])
    settings["dbname"] = db_name
    return settings


def _load_migrations(migrations_folder: str | Path) -> list[tuple[int, Path]]:
    """Return SQL migration files sorted by their numeric filename prefix."""
    folder = Path(migrations_folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"Migration folder does not exist: {folder}")

    migrations = []
    versions = set()
    for path in folder.iterdir():
        if path.suffix.lower() != ".sql":
            continue

        match = _MIGRATION_FILE_PATTERN.fullmatch(path.name)
        if match is None:
            raise ValueError(
                f"Migration filename must start with a number: {path.name}"
            )

        version = int(match.group(1))
        if version < 1:
            raise ValueError(f"Migration versions must be positive: {path.name}")
        if version in versions:
            raise ValueError(f"Duplicate migration version {version} in {folder}")
        versions.add(version)
        migrations.append((version, path))

    return sorted(migrations, key=lambda migration: migration[0])


def run_migrations(db_name: str) -> int:
    """Apply pending SQL migrations for a database named ``db_name``.

    The database connection settings are loaded from
    ``/db_config/{db_name}.yml``. String values may reference
    environment variables using ``${VARIABLE_NAME}``; the YAML mapping must
    provide ``host``, ``port``, ``username`` (or ``user``), and ``password``.
    Numbered SQL migration files are loaded from
    ``/migrations/scripts/{db_name}/``.

    Args:
        db_name: Database name and matching config/migration directory key.

    Returns:
        The latest migration version recorded in the database after execution.

    Raises:
        FileNotFoundError: If the database configuration file is missing.
        NotADirectoryError: If the migration scripts directory does not exist.
        ValueError: If configuration is invalid, an environment variable is
            unset, or migration filenames are invalid or duplicated.
        RuntimeError: If the database version is newer than available scripts.
        psycopg.Error: If connecting or executing a migration fails.
    """
    settings = _load_database_config(db_name)
    migration_folder = MIGRATIONS_ROOT / "scripts" / db_name
    migrations = [
        (version, path, path.read_text(encoding="utf-8"))
        for version, path in _load_migrations(migration_folder)
    ]

    with psycopg.connect(**settings) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (_MIGRATION_ADVISORY_LOCK_ID,),
            )
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    id SMALLINT PRIMARY KEY CHECK (id = 1),
                    version BIGINT NOT NULL CHECK (version >= 0)
                )
                """
            )
            cursor.execute(
                f"""
                INSERT INTO {MIGRATION_TABLE} (id, version)
                VALUES (1, 0)
                ON CONFLICT (id) DO NOTHING
                """
            )
            cursor.execute(
                f"SELECT version FROM {MIGRATION_TABLE} WHERE id = 1"
            )
            current_version = cursor.fetchone()[0]

            latest_file_version = migrations[-1][0] if migrations else 0
            if current_version > latest_file_version:
                raise RuntimeError(
                    f"Database version {current_version} is newer than the "
                    f"latest available migration version {latest_file_version}"
                )

            for version, _path, sql in migrations:
                if version <= current_version:
                    continue

                if sql.strip():
                    cursor.execute(sql)
                cursor.execute(
                    f"UPDATE {MIGRATION_TABLE} SET version = %s WHERE id = 1",
                    (version,),
                )
                current_version = version

    return current_version
