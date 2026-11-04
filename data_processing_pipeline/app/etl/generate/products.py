import random

import pandas as pd


def generate_prices(
    table: pd.DataFrame,
    column_name: str,
    floor: float,
    ceiling: float,
) -> pd.DataFrame:
    """Return a copy of ``table`` with random prices in the inclusive range."""
    if not column_name:
        raise ValueError("column_name must not be empty")
    if floor > ceiling:
        raise ValueError("floor must be less than or equal to ceiling")

    result = table.copy()
    result[column_name] = [
        round(random.uniform(floor, ceiling), 2) for _ in range(len(result))
    ]
    return result


def give_new_prices(
    table: pd.DataFrame,
    chance_of_new_price: float | None = None,
    max_change_percent: float = 0,
    *,
    change_of_new_price: float | None = None,
) -> pd.DataFrame:
    """Randomly change product prices by up to ``max_change_percent`` percent.

    Each row's price changes independently with probability
    ``chance_of_new_price``. ``change_of_new_price`` is accepted as an alias.
    """
    if chance_of_new_price is None:
        chance_of_new_price = change_of_new_price
    if chance_of_new_price is None:
        raise TypeError("chance_of_new_price must be provided")
    if not 0 <= chance_of_new_price <= 1:
        raise ValueError("change_of_new_price must be between 0 and 1")
    if not 0 <= max_change_percent <= 100:
        raise ValueError("max_change_percent must be between 0 and 100")
    if "current_price" not in table.columns:
        raise KeyError("table must contain a 'current_price' column")

    result = table.copy()
    price_column = result.columns.get_loc("current_price")
    for position in range(len(result)):
        price = result.iloc[position, price_column]
        if pd.isna(price) or random.random() >= chance_of_new_price:
            continue

        change_percent = random.uniform(
            -max_change_percent,
            max_change_percent,
        )
        result.iloc[position, price_column] = round(
            price * (1 + change_percent / 100),
            2,
        )

    return result