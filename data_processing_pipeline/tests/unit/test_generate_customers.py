import pandas as pd
import pytest

from app.etl.generate.customers import generate_customers, give_new_addresses


def test_generate_customers_returns_schema_fields_and_sequential_ids():
    result = generate_customers(num_customers=3, current_max_id=10)

    assert list(result.columns) == [
        "customer_id",
        "customer_name",
        "gender",
        "birthday",
        "address",
    ]
    assert result["customer_id"].tolist() == [11, 12, 13]
    assert result["customer_name"].notna().all()
    assert result["gender"].isin(["female", "male"]).all()
    assert result["birthday"].notna().all()
    assert result["address"].notna().all()


def test_generate_customers_uses_name_matching_selected_gender(monkeypatch):
    class Fake:
        genders = iter(("female", "male"))

        def random_element(self, elements):
            return next(self.genders)

        def name_female(self):
            return "Female Name"

        def name_male(self):
            return "Male Name"

        def date_of_birth(self, minimum_age, maximum_age):
            return None

        def address(self):
            return "Fake Address"

    monkeypatch.setattr("app.etl.generate.customers.Faker", Fake)

    result = generate_customers(num_customers=2, current_max_id=0)

    assert result[["customer_name", "gender"]].values.tolist() == [
        ["Female Name", "female"],
        ["Male Name", "male"],
    ]


def test_generate_customers_returns_empty_dataframe_with_expected_columns():
    result = generate_customers(num_customers=0, current_max_id=10)

    assert result.empty
    assert list(result.columns) == [
        "customer_id",
        "customer_name",
        "gender",
        "birthday",
        "address",
    ]


def test_generate_customers_rejects_negative_count():
    with pytest.raises(ValueError, match="must not be negative"):
        generate_customers(num_customers=-1, current_max_id=0)


def test_give_new_addresses_changes_requested_random_fraction_and_returns_all_rows():
    customers = pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4],
            "address": ["Old address"] * 4,
        }
    )

    result = give_new_addresses(customers, change_of_new_address=0.5)

    assert len(result) == len(customers)
    assert (result["address"] != customers["address"]).sum() == 2
    assert (customers["address"] == "Old address").all()


def test_give_new_addresses_rejects_ratio_outside_zero_to_one():
    customers = pd.DataFrame({"address": ["Old address"]})

    with pytest.raises(ValueError, match="between 0 and 1"):
        give_new_addresses(customers, change_of_new_address=1.1)


def test_give_new_addresses_rejects_missing_address_column():
    with pytest.raises(KeyError, match="address"):
        give_new_addresses(pd.DataFrame({"customer_id": [1]}), 0.5)
