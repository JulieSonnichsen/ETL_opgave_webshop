import argparse
from collections.abc import Sequence

from .runner import run_migrations


def main(argv: Sequence[str] | None = None) -> None:
    """Run migrations for each database name provided on the command line.

    Args:
        argv: Optional command-line arguments, excluding the program name.
            When omitted, arguments are read from the process command line.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--db_names", nargs="+", required=True, metavar="DB_NAME")
    args = parser.parse_args(argv)

    for db_name in args.db_names:
        run_migrations(db_name=db_name)


if __name__ == "__main__":
    main()
