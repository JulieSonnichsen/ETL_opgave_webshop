import pandas as pd

def combine_tables(tables: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack DataFrames, preserving all columns and filling missing values.

    Columns present in only some input tables are retained; rows from tables
    without those columns receive ``NaN`` for those fields.
    """
    return pd.concat(tables, ignore_index=True, sort=False)

def random_join(left_table: pd.DataFrame, right_table: pd.DataFrame, right_table_columns: list[str]) -> pd.DataFrame:
    """Append randomly selected right-table values to every left-table row.

    Right-table rows are sampled with replacement, so every left row receives
    a match even when the right table has fewer rows. Only the requested right
    table columns are included.
    """
    if not right_table_columns:
        raise ValueError("right_table_columns must contain at least one column")
    if left_table.empty:
        right_values = right_table.loc[:, right_table_columns].iloc[0:0]
    else:
        if right_table.empty:
            raise ValueError("right_table must contain rows to match")
        right_values = right_table.loc[:, right_table_columns].sample(
            n=len(left_table),
            replace=True,
        )

    left_values = left_table.reset_index(drop=True)
    right_values = right_values.reset_index(drop=True)
    overlapping_columns = set(left_values.columns) & set(right_values.columns)
    if overlapping_columns:
        right_values = right_values.rename(
            columns={
                column: f"{column}_right"
                for column in overlapping_columns
            }
        )
    return pd.concat([left_values, right_values], axis=1)

def add_column_with_value(table: pd.DataFrame, column_name: str, value: object) -> pd.DataFrame:
    """Return a copy of ``table`` with ``column_name`` set to ``value``."""
    result = table.copy()
    result[column_name] = value
    return result

def pull_columns_to_table(
    table: pd.DataFrame,
    columns_to_keep: list[str],
    id_column: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Normalize non-kept columns into record values and a column-name lookup.

    Returns the original table restricted to ``columns_to_keep`` (always
    including ``id_column``), a values table with ``record_id``, ``column_id``,
    and ``value`` columns, and a lookup table with ``id`` and ``name`` columns.
    """
    if id_column not in table.columns:
        raise ValueError(f"id_column {id_column!r} is not present in the table")
    missing_columns = [
        column for column in columns_to_keep if column not in table.columns
    ]
    if missing_columns:
        raise ValueError(
            "columns_to_keep contains columns not present in the table: "
            + ", ".join(missing_columns)
        )

    kept_columns = list(dict.fromkeys([id_column, *columns_to_keep]))
    pulled_columns = [
        column for column in table.columns if column not in kept_columns
    ]

    original_table = table.loc[:, kept_columns].copy()
    column_ids = {
        column_name: column_id
        for column_id, column_name in enumerate(pulled_columns, start=1)
    }

    values_table = table.melt(
        id_vars=[id_column],
        value_vars=pulled_columns,
        var_name="name",
        value_name="value",
    ).rename(columns={id_column: "record_id"})
    values_table["column_id"] = values_table["name"].map(column_ids)
    values_table = values_table.loc[:, ["record_id", "column_id", "value"]]

    name_lookup = pd.DataFrame(
        {
            "id": list(column_ids.values()),
            "name": list(column_ids.keys()),
        }
    )
    return original_table, values_table, name_lookup

def map_columns(table: pd.DataFrame, column_mapping: dict) -> pd.DataFrame:
    """Keep mapped source columns and rename them to their mapped names."""
    mapped_table = table.loc[:, list(column_mapping)].copy()
    return mapped_table.rename(columns=column_mapping)

def remove_columns(table: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return a copy of ``table`` without the specified columns.

    Raises:
        KeyError: If any requested column is not present in the table.
    """
    return table.drop(columns=columns)


def shuffle_table(table: pd.DataFrame) -> pd.DataFrame:
    """Return all table rows in a random order with a fresh sequential index."""
    return table.sample(frac=1).reset_index(drop=True)


def give_ids(
    table: pd.DataFrame,
    id_column_name: str,
    start_id: int = 0,
) -> pd.DataFrame:
    """Return a copy of ``table`` with sequential IDs starting at ``start_id``."""
    result = table.copy()
    result[id_column_name] = range(start_id, start_id + len(result))
    return result


def remove_duplicate_by_composite_columns(table: pd.DataFrame, composite_columns: list[str]) -> pd.DataFrame:
    """Keep the first row for each unique combination of key-column values.

    All columns are retained, and the input table is not modified.

    Raises:
        ValueError: If no composite key columns are provided.
        KeyError: If any key column is missing from the table.
    """
    if not composite_columns:
        raise ValueError("composite_columns must contain at least one column")
    return table.drop_duplicates(subset=composite_columns, keep="first")


def remove_null_records(table: pd.DataFrame, column: str) -> pd.DataFrame:
    """Return rows where ``column`` is not null.

    Raises:
        KeyError: If ``column`` is not present in the table.
    """
    return table.dropna(subset=[column])


def filter_updated_records(
    original_table: pd.DataFrame,
    updated_table: pd.DataFrame,
) -> pd.DataFrame:
    """Return rows from ``updated_table`` that differ from the original rows.

    The DataFrames must have matching indexes and columns. Null values in the
    same positions are treated as unchanged.
    """
    if not original_table.index.equals(updated_table.index):
        raise ValueError("DataFrames must have matching indexes")
    if not original_table.columns.equals(updated_table.columns):
        raise ValueError("DataFrames must have matching columns")

    original_missing = original_table.isna()
    updated_missing = updated_table.isna()
    unchanged = (
        original_table.eq(updated_table).fillna(False)
        & ~original_missing
        & ~updated_missing
    ) | (original_missing & updated_missing)
    changed_rows = ~unchanged.all(axis=1)
    return updated_table.loc[changed_rows]