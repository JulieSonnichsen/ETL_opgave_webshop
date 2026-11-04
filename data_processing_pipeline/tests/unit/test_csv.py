import pandas as pd

from app.etl.extract.csv import read_csv_file


def test_read_csv_file_returns_dataframe_using_specified_encoding(tmp_path):
    csv_path = tmp_path / "products.csv"
    csv_path.write_text(
        "name,price\nLaptop,999\nCaf\u00e9 tablet,499\n",
        encoding="utf-8",
    )

    result = read_csv_file(str(csv_path), encoding="utf-8")

    expected = pd.DataFrame(
        {
            "name": ["Laptop", "Caf\u00e9 tablet"],
            "price": [999, 499],
        }
    )
    pd.testing.assert_frame_equal(result, expected)


def test_read_csv_file_reads_cp1252_encoded_csv(tmp_path):
    csv_path = tmp_path / "products.csv"
    csv_path.write_bytes("name,price\nCafé,499\n".encode("cp1252"))

    result = read_csv_file(str(csv_path), encoding="cp1252")

    expected = pd.DataFrame({"name": ["Café"], "price": [499]})
    pd.testing.assert_frame_equal(result, expected)
