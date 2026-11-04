from datetime import date, datetime, timedelta

import pandas as pd
import pytest

from app.etl.generate.orders import generate_orders


def test_generate_orders_and_lines_match_internal_schema_and_limits():
    customers = pd.DataFrame(
        {
            "customer_id": [4, 5],
            "address": ["One Main Street", "Two Main Street"],
        }
    )
    products = pd.DataFrame(
        {
            "product_id": [10, 11],
            "current_price": [12.5, 23.75],
        }
    )

    orders, order_lines = generate_orders(
        product_table=products,
        customer_table=customers,
        num_orders=2,
        starttime=date(2025, 1, 1),
        endtime=date(2025, 1, 10),
        max_order_lines=4,
        max_quantity=5,
        current_max_order_id=100,
        current_max_order_line_id=200,
    )

    assert list(orders.columns) == [
        "order_id",
        "customer_id",
        "address",
        "order_date",
    ]
    assert list(order_lines.columns) == [
        "order_line_id",
        "order_id",
        "product_id",
        "quantity",
        "price",
    ]
    assert orders["order_id"].tolist() == [101, 102]
    assert orders["customer_id"].is_unique
    assert order_lines["order_line_id"].tolist() == list(
        range(201, 201 + len(order_lines))
    )
    assert order_lines.groupby("order_id").size().between(1, 4).all()
    assert order_lines["quantity"].between(1, 5).all()
    assert order_lines["product_id"].isin(products["product_id"]).all()
    assert order_lines["price"].isin(products["current_price"]).all()
    assert orders["customer_id"].isin(customers["customer_id"]).all()
    assert orders["address"].isin(customers["address"]).all()
    assert orders["order_date"].between(
        datetime(2025, 1, 1),
        datetime(2025, 1, 10, 23, 59, 59, 999999),
    ).all()


def test_generate_orders_samples_times_across_datetime_range(monkeypatch):
    customers = pd.DataFrame(
        {"customer_id": [1], "address": ["One Street"]}
    )
    products = pd.DataFrame(
        {"product_id": [1], "current_price": [10.0]}
    )
    starttime = datetime(2025, 1, 1, 9, 30)
    endtime = starttime + timedelta(hours=2)
    monkeypatch.setattr(
        "app.etl.generate.orders.random.randint",
        lambda lower, upper: upper // 2,
    )

    orders, _ = generate_orders(
        product_table=products,
        customer_table=customers,
        num_orders=1,
        starttime=starttime,
        endtime=endtime,
        max_order_lines=1,
        max_quantity=1,
    )

    assert orders.loc[0, "order_date"] == starttime + timedelta(hours=1)


def test_generate_orders_returns_empty_tables_for_zero_orders():
    customers = pd.DataFrame(columns=["customer_id", "address"])
    products = pd.DataFrame(columns=["product_id", "current_price"])

    orders, order_lines = generate_orders(
        product_table=products,
        customer_table=customers,
        num_orders=0,
        starttime=date(2025, 1, 1),
        endtime=date(2025, 1, 10),
        max_order_lines=3,
        max_quantity=4,
    )

    assert orders.empty
    assert order_lines.empty
    assert list(orders.columns) == [
        "order_id",
        "customer_id",
        "address",
        "order_date",
    ]
    assert list(order_lines.columns) == [
        "order_line_id",
        "order_id",
        "product_id",
        "quantity",
        "price",
    ]


def test_generate_orders_requires_products_when_orders_requested():
    customers = pd.DataFrame({"customer_id": [1], "address": ["One Street"]})
    products = pd.DataFrame(columns=["product_id", "current_price"])

    with pytest.raises(ValueError, match="product_table must contain products"):
        generate_orders(
            product_table=products,
            customer_table=customers,
            num_orders=1,
            starttime=date(2025, 1, 1),
            endtime=date(2025, 1, 10),
            max_order_lines=3,
            max_quantity=4,
        )


def test_generate_orders_rejects_more_orders_than_available_customers():
    customers = pd.DataFrame(
        {"customer_id": [1], "address": ["One Street"]}
    )
    products = pd.DataFrame(
        {"product_id": [1], "current_price": [10.0]}
    )

    with pytest.raises(ValueError, match="cannot exceed the number"):
        generate_orders(
            product_table=products,
            customer_table=customers,
            num_orders=2,
            starttime=date(2025, 1, 1),
            endtime=date(2025, 1, 10),
            max_order_lines=3,
            max_quantity=4,
        )
