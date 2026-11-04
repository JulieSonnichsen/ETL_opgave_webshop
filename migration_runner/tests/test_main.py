from unittest.mock import call, patch

from app.main import main


def test_main_runs_migrations_for_each_requested_database():
    with patch("app.main.run_migrations") as run_migrations:
        main(["--db_names", "internal_db", "api_db"])

    assert run_migrations.call_args_list == [
        call(db_name="internal_db"),
        call(db_name="api_db"),
    ]
