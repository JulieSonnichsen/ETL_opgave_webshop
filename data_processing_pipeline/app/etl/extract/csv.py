import pandas as pd


def read_csv_file(path: str, encoding: str) -> pd.DataFrame:
    """Read a CSV file into a DataFrame using the specified encoding."""
    return pd.read_csv(path, encoding=encoding)