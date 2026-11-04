


import os
import re
from collections.abc import Mapping
from pathlib import Path

import psycopg

import yaml


DB_CONFIG_ROOT = Path("/db_config")
_ENVIRONMENT_VARIABLE_PATTERN = re.compile(r"\$\{([^}]+)\}")


class DBConnector():
    """Manage database connections and their queued SQL queries."""

    def __init__(self):
        """Initialize an empty collection of database connections."""
        self.connections = {}

    def connect(self, db_name: str):
        """Open and store a connection unless one is already open."""
        existing_connection = self.connections.get(db_name)
        if (
            existing_connection is not None
            and not existing_connection["connection"].closed
        ):
            return

        db_config = _read_db_config(db_name=db_name)

        conn = psycopg.connect(
            host=db_config["host"],
            port=db_config["port"],
            user=db_config["username"],
            password=db_config["password"],
            dbname=db_config["db_name"],
        )

        cursor = conn.cursor()
        self.connections[db_name] = {
            "connection": conn,
            "cursor": cursor,
            "querie_queue": (
                existing_connection["querie_queue"]
                if existing_connection is not None
                else []
            ),
        }


    def close_connection(self, db_name: str):
        """Close the stored connection for the named database."""
        self.connections[db_name]["connection"].close()

    def add_query(self, db_name: str, query: str, vars = None):
        """Add a SQL query and optional parameters to the connection queue."""
        self.connections[db_name]["querie_queue"].append({
            "query": query,
            "vars": vars
        })

    def commit_queries(self, db_name: str) -> None:
        """Execute all queued queries in one transaction.

        On failure, roll back the transaction and retain the queued queries.
        Clear the queue only after the transaction commits successfully.
        """
        connection_info = self.connections[db_name]
        connection = connection_info["connection"]
        cursor = connection_info["cursor"]
        query_queue = connection_info["querie_queue"]

        try:
            for queued_query in query_queue:
                if queued_query["vars"] is None:
                    cursor.execute(queued_query["query"])
                else:
                    cursor.execute(queued_query["query"], queued_query["vars"])
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        query_queue.clear()




_db = None

def get_dbconnector() -> DBConnector:
    """Return the process-wide database connector instance."""
    global _db

    if _db is None:
        _db = DBConnector()

    return _db


def _resolve_environment_variables(value: object) -> object:
    """Recursively replace ``${NAME}`` references in strings with env values.

    Raises:
        ValueError: If an environment variable referenced in a value is unset.
    """
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            try:
                return os.environ[name]
            except KeyError as error:
                raise ValueError(
                    f"Environment variable {name!r} used in database config "
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


def _read_db_config(db_name: str) -> dict[str, object]:
    """Load the YAML config for ``db_name`` and resolve its env references.

    The config is read from ``{DB_CONFIG_ROOT}/{db_name}.yml`` and the
    returned mapping includes ``db_name``.

    Raises:
        ValueError: If ``db_name`` is a path or the YAML is not a mapping.
        FileNotFoundError: If the matching config file does not exist.
    """
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

    db_config = dict(config)
    db_config["db_name"] = db_name
    return db_config