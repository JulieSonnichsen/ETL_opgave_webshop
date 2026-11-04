import random

from faker import Faker
import pandas as pd


def generate_customers(num_customers: int, current_max_id: int) -> pd.DataFrame:
    """Generate customers with IDs after ``current_max_id`` and fake details."""
    if num_customers < 0:
        raise ValueError("num_customers must not be negative")

    fake = Faker()
    customers = []
    for index in range(num_customers):
        gender = fake.random_element(elements=("female", "male"))
        name = fake.name_female() if gender == "female" else fake.name_male()
        customers.append(
            {
                "customer_id": current_max_id + index + 1,
                "customer_name": name,
                "gender": gender,
                "birthday": fake.date_of_birth(minimum_age=18, maximum_age=90),
                "address": fake.address(),
            }
        )
    return pd.DataFrame(
        customers,
        columns=[
            "customer_id",
            "customer_name",
            "gender",
            "birthday",
            "address",
        ],
    )


def give_new_addresses(
    customers: pd.DataFrame,
    chance_of_new_address: float | None = None,
    *,
    change_of_new_address: float | None = None,
) -> pd.DataFrame:
    """Replace addresses for a random fraction of customers and return all rows.

    ``chance_of_new_address`` and ``change_of_new_address`` are aliases for the
    same probability, which must be between 0 and 1 inclusive.
    """
    if chance_of_new_address is None:
        chance_of_new_address = change_of_new_address
    if chance_of_new_address is None:
        raise TypeError("chance_of_new_address must be provided")
    if not 0 <= chance_of_new_address <= 1:
        raise ValueError("change_of_new_address must be between 0 and 1")
    if "address" not in customers.columns:
        raise KeyError("customers must contain an 'address' column")

    result = customers.copy()
    num_addresses = round(len(result) * chance_of_new_address)
    selected_positions = random.sample(range(len(result)), num_addresses)
    address_column = result.columns.get_loc("address")
    fake = Faker()
    for position in selected_positions:
        result.iloc[position, address_column] = fake.address()

    return result