import pandas as pd
import pytest

from app.etl.generate import products
from app.etl.generate.products import generate_prices, give_new_prices


def test_generate_prices_adds_random_values_within_range_without_mutating_table():
    table = pd.DataFrame({"product_id": [1, 2, 3]})

    result = generate_prices(table, "price", 10.0, 100.0)

    assert result["price"].between(10.0, 100.0).all()
    assert result["price"].map(lambda price: round(price, 2) == price).all()
    assert len(result) == len(table)
    assert "price" not in table.columns


def test_generate_prices_rejects_empty_column_name():
    with pytest.raises(ValueError, match="column_name"):
        generate_prices(pd.DataFrame({"product_id": [1]}), "", 10.0, 100.0)


def test_generate_prices_rejects_floor_above_ceiling():
    with pytest.raises(ValueError, match="floor"):
        generate_prices(pd.DataFrame({"product_id": [1]}), "price", 100.0, 10.0)


def test_give_new_prices_changes_each_price_within_percentage_and_rounds(
    monkeypatch,
):
    table = pd.DataFrame({"current_price": [10.0, 20.0, 30.0]})
    chance_draws = iter([0.1, 0.9, 0.2])
    percent_changes = iter([10.0, -10.0])
    monkeypatch.setattr(products.random, "random", lambda: next(chance_draws))
    monkeypatch.setattr(
        products.random,
        "uniform",
        lambda lower, upper: next(percent_changes),
    )

    result = give_new_prices(table, change_of_new_price=0.5, max_change_percent=10)

    assert result["current_price"].tolist() == [11.0, 20.0, 27.0]
    assert table["current_price"].tolist() == [10.0, 20.0, 30.0]


def test_give_new_prices_does_not_change_prices_when_chance_is_zero(monkeypatch):
    table = pd.DataFrame({"current_price": [10.123, 20.0]})
    monkeypatch.setattr(
        products.random,
        "random",
        lambda: 0.5,
    )

    result = give_new_prices(table, change_of_new_price=0, max_change_percent=10)

    pd.testing.assert_frame_equal(result, table)


def test_give_new_prices_rejects_invalid_probability_and_change_percent():
    table = pd.DataFrame({"current_price": [10.0]})

    with pytest.raises(ValueError, match="change_of_new_price"):
        give_new_prices(table, change_of_new_price=1.1, max_change_percent=10)
    with pytest.raises(ValueError, match="max_change_percent"):
        give_new_prices(table, change_of_new_price=0.5, max_change_percent=101)


def test_give_new_prices_requires_current_price_column():
    with pytest.raises(KeyError, match="current_price"):
        give_new_prices(pd.DataFrame({"price": [10.0]}), 0.5, 10)
