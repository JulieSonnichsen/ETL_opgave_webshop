import pandas as pd

import pytest

from app.etl.transform.dataframe_utils import (
    add_column_with_value,
    combine_tables,
    give_ids,
    map_columns,
    pull_columns_to_table,
    remove_duplicate_by_composite_columns,
    remove_columns,
    remove_null_records,
    filter_updated_records,
    random_join,
    shuffle_table,
)


def test_combine_tables_keeps_union_of_columns_and_fills_missing_values():
    first_table = pd.DataFrame(
        {
            "product": ["Laptop"],
            "memory_gb": [16],
        }
    )
    second_table = pd.DataFrame(
        {
            "product": ["Tablet"],
            "screen_size": [11],
        }
    )

    result = combine_tables([first_table, second_table])

    assert list(result.columns) == ["product", "memory_gb", "screen_size"]
    assert result.loc[0, "product"] == "Laptop"
    assert result.loc[0, "memory_gb"] == 16
    assert pd.isna(result.loc[0, "screen_size"])
    assert result.loc[1, "product"] == "Tablet"
    assert pd.isna(result.loc[1, "memory_gb"])
    assert result.loc[1, "screen_size"] == 11.0
    assert list(result.index) == [0, 1]


def test_combine_tables_handles_empty_input_tables():
    result = combine_tables(
        [
            pd.DataFrame({"product": ["Laptop"]}),
            pd.DataFrame(columns=["product", "screen_size"]),
        ]
    )

    assert list(result.columns) == ["product", "screen_size"]
    assert result.loc[0, "product"] == "Laptop"
    assert pd.isna(result.loc[0, "screen_size"])


def test_add_column_with_value_sets_value_for_all_rows_without_mutating_input():
    table = pd.DataFrame({"product": ["Laptop", "Tablet"]})

    result = add_column_with_value(table, "category", "electronics")

    assert result["category"].tolist() == ["electronics", "electronics"]
    assert list(table.columns) == ["product"]


def test_add_column_with_value_replaces_existing_column():
    table = pd.DataFrame({"category": ["old", "old"]})

    result = add_column_with_value(table, "category", "new")

    assert result["category"].tolist() == ["new", "new"]


def test_pull_columns_to_table_returns_kept_values_and_name_lookup():
    table = pd.DataFrame(
        {
            "product_id": [10, 20],
            "name": ["Laptop", "Tablet"],
            "memory_gb": [16, 8],
            "screen_size": [pd.NA, 11],
        }
    )

    original, values, names = pull_columns_to_table(
        table,
        columns_to_keep=["name"],
        id_column="product_id",
    )

    pd.testing.assert_frame_equal(
        original,
        pd.DataFrame(
            {
                "product_id": [10, 20],
                "name": ["Laptop", "Tablet"],
            }
        ),
    )
    assert values["record_id"].tolist() == [10, 20, 10, 20]
    assert values["column_id"].tolist() == [1, 1, 2, 2]
    assert values.loc[0, "value"] == 16
    assert values.loc[1, "value"] == 8
    assert pd.isna(values.loc[2, "value"])
    assert values.loc[3, "value"] == 11
    pd.testing.assert_frame_equal(
        names,
        pd.DataFrame(
            {
                "id": [1, 2],
                "name": ["memory_gb", "screen_size"],
            }
        ),
    )


def test_pull_columns_to_table_returns_empty_value_tables_when_nothing_to_pull():
    table = pd.DataFrame({"product_id": [1], "name": ["Laptop"]})

    original, values, names = pull_columns_to_table(
        table,
        columns_to_keep=["name"],
        id_column="product_id",
    )

    assert list(original.columns) == ["product_id", "name"]
    assert list(values.columns) == ["record_id", "column_id", "value"]
    assert values.empty
    assert list(names.columns) == ["id", "name"]
    assert names.empty


def test_pull_columns_to_table_requires_record_id_column():
    with pytest.raises(ValueError, match="id_column"):
        pull_columns_to_table(
            pd.DataFrame({"name": ["Laptop"]}),
            columns_to_keep=["name"],
            id_column="product_id",
        )


def test_map_columns_keeps_and_renames_only_mapped_columns():
    table = pd.DataFrame(
        {
            "source_id": [1, 2],
            "source_name": ["Laptop", "Tablet"],
            "unused": ["x", "y"],
        }
    )

    result = map_columns(
        table,
        {"source_id": "product_id", "source_name": "product_name"},
    )

    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame(
            {
                "product_id": [1, 2],
                "product_name": ["Laptop", "Tablet"],
            }
        ),
    )
    assert list(table.columns) == ["source_id", "source_name", "unused"]


def test_map_columns_raises_for_missing_source_column():
    with pytest.raises(KeyError):
        map_columns(pd.DataFrame({"name": ["Laptop"]}), {"missing": "product"})


def test_remove_columns_drops_requested_columns_without_mutating_input():
    table = pd.DataFrame(
        {
            "product_id": [1, 2],
            "name": ["Laptop", "Tablet"],
            "unused": ["x", "y"],
        }
    )

    result = remove_columns(table, ["unused"])

    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame(
            {
                "product_id": [1, 2],
                "name": ["Laptop", "Tablet"],
            }
        ),
    )
    assert "unused" in table.columns


def test_remove_columns_raises_for_missing_column():
    with pytest.raises(KeyError):
        remove_columns(pd.DataFrame({"name": ["Laptop"]}), ["missing"])


def test_remove_null_records_drops_rows_null_in_specified_column():
    table = pd.DataFrame(
        {
            "product_id": [1, 2, 3],
            "specification_id": [1, pd.NA, 3],
            "value": ["16GB", "8GB", "512GB"],
        }
    )

    result = remove_null_records(table, "specification_id")

    pd.testing.assert_frame_equal(result, table.loc[[0, 2]])
    assert len(table) == 3


def test_remove_null_records_raises_for_missing_column():
    with pytest.raises(KeyError):
        remove_null_records(pd.DataFrame({"name": ["Laptop"]}), "missing")


def test_filter_updated_records_returns_changed_rows_from_updated_table():
    original = pd.DataFrame(
        {"customer_id": [1, 2, 3], "address": ["A", "B", None]},
        index=[5, 6, 7],
    )
    updated = pd.DataFrame(
        {"customer_id": [1, 2, 3], "address": ["A", "New B", None]},
        index=[5, 6, 7],
    )

    result = filter_updated_records(original, updated)

    pd.testing.assert_frame_equal(result, updated.loc[[6]])
    assert original.loc[6, "address"] == "B"


def test_filter_updated_records_returns_empty_when_dataframes_are_equal():
    table = pd.DataFrame({"customer_id": [1], "address": [None]})

    result = filter_updated_records(table, table.copy())

    pd.testing.assert_frame_equal(result, table.iloc[0:0])


def test_filter_updated_records_treats_null_to_value_as_an_update():
    original = pd.DataFrame({"address": [pd.NA]}, dtype="string")
    updated = pd.DataFrame({"address": ["New address"]}, dtype="string")

    result = filter_updated_records(original, updated)

    pd.testing.assert_frame_equal(result, updated)


def test_filter_updated_records_requires_matching_indexes_and_columns():
    original = pd.DataFrame({"address": ["A"]}, index=[1])

    with pytest.raises(ValueError, match="matching indexes"):
        filter_updated_records(original, original.set_axis([2]))

    with pytest.raises(ValueError, match="matching columns"):
        filter_updated_records(
            original,
            original.rename(columns={"address": "location"}),
        )


def test_random_join_keeps_all_left_rows_and_only_requested_right_columns():
    left_table = pd.DataFrame(
        {"left_id": [10, 20, 30], "shared": ["a", "b", "c"]},
        index=[5, 6, 7],
    )
    right_table = pd.DataFrame(
        {
            "shared": ["x", "y"],
            "category": ["laptop", "tablet"],
            "unused": ["ignore-1", "ignore-2"],
        }
    )

    result = random_join(left_table, right_table, ["shared", "category"])

    assert len(result) == len(left_table)
    assert result["left_id"].tolist() == [10, 20, 30]
    assert result["shared"].tolist() == ["a", "b", "c"]
    assert result["shared_right"].isin(["x", "y"]).all()
    assert result["category"].isin(["laptop", "tablet"]).all()
    assert "unused" not in result.columns
    assert all(
        (shared, category) in {("x", "laptop"), ("y", "tablet")}
        for shared, category in zip(
            result["shared_right"], result["category"]
        )
    )


def test_random_join_allows_empty_left_table():
    left_table = pd.DataFrame(columns=["left_id"])
    right_table = pd.DataFrame({"category": ["laptop"]})

    result = random_join(left_table, right_table, ["category"])

    assert list(result.columns) == ["left_id", "category"]
    assert result.empty


def test_random_join_rejects_empty_right_table_for_nonempty_left():
    left_table = pd.DataFrame({"left_id": [1]})
    right_table = pd.DataFrame(columns=["category"])

    with pytest.raises(ValueError, match="right_table must contain rows"):
        random_join(left_table, right_table, ["category"])


def test_random_join_rejects_empty_column_selection():
    with pytest.raises(ValueError, match="at least one column"):
        random_join(
            pd.DataFrame({"left_id": [1]}),
            pd.DataFrame({"category": ["laptop"]}),
            [],
        )


def test_shuffle_table_shuffles_rows_and_resets_index(monkeypatch):
    table = pd.DataFrame(
        {"product_id": [1, 2, 3]},
        index=[5, 6, 7],
    )
    sample_calls = []

    def reverse_sample(dataframe, frac):
        sample_calls.append(frac)
        return dataframe.iloc[::-1]

    monkeypatch.setattr(pd.DataFrame, "sample", reverse_sample)

    result = shuffle_table(table)

    assert sample_calls == [1]
    assert result["product_id"].tolist() == [3, 2, 1]
    assert result.index.tolist() == [0, 1, 2]
    assert table["product_id"].tolist() == [1, 2, 3]


def test_shuffle_table_handles_empty_table():
    table = pd.DataFrame(columns=["product_id"])

    result = shuffle_table(table)

    assert result.empty
    assert list(result.columns) == ["product_id"]


def test_give_ids_assigns_ids_from_start_id_without_mutating_input():
    table = pd.DataFrame({"name": ["Laptop", "Tablet", "Phone"]})

    result = give_ids(table, "product_id", start_id=12)

    assert result["product_id"].tolist() == [12, 13, 14]
    assert result["name"].tolist() == ["Laptop", "Tablet", "Phone"]
    assert "product_id" not in table.columns


def test_give_ids_replaces_existing_id_column():
    table = pd.DataFrame({"product_id": [100, 200], "name": ["Laptop", "Tablet"]})

    result = give_ids(table, "product_id", start_id=1)

    assert result["product_id"].tolist() == [1, 2]
    assert table["product_id"].tolist() == [100, 200]


def test_give_ids_adds_empty_id_column_to_empty_table():
    result = give_ids(pd.DataFrame({"name": []}), "product_id")

    assert result.empty
    assert list(result.columns) == ["name", "product_id"]


def test_remove_duplicate_by_composite_columns_keeps_first_matching_row():
    table = pd.DataFrame(
        {
            "manufacturer": ["Acme", "Acme", "Acme", "Globex"],
            "model": ["A", "A", "B", "A"],
            "price": [100, 120, 200, 150],
        },
        index=[5, 6, 7, 8],
    )

    result = remove_duplicate_by_composite_columns(
        table,
        ["manufacturer", "model"],
    )

    pd.testing.assert_frame_equal(
        result,
        table.loc[[5, 7, 8]],
    )
    assert len(table) == 4
    assert table.loc[6, "price"] == 120


def test_remove_duplicate_by_composite_columns_requires_key_columns():
    with pytest.raises(ValueError, match="at least one column"):
        remove_duplicate_by_composite_columns(
            pd.DataFrame({"model": ["A"]}),
            [],
        )


def test_remove_duplicate_by_composite_columns_raises_for_missing_key():
    with pytest.raises(KeyError):
        remove_duplicate_by_composite_columns(
            pd.DataFrame({"model": ["A"]}),
            ["manufacturer"],
        )
