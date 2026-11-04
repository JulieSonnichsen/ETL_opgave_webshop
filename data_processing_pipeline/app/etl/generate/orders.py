import random
from datetime import date, datetime, time, timedelta

import pandas as pd


def _skewed_random_int(max_value: int, decay: float) -> int:
    """Choose an integer from 1 to max_value using configurable decay weights."""
    values = list(range(1, max_value + 1))
    weights = [decay ** (value - 1) for value in values]
    return random.choices(values, weights=weights, k=1)[0]


def generate_orders(
    product_table: pd.DataFrame,
    customer_table: pd.DataFrame,
    num_orders: int,
    starttime: datetime | date,
    endtime: datetime | date,
    max_order_lines: int,
    max_quantity: int,
    current_max_order_id: int = 0,
    current_max_order_line_id: int = 0,
    line_count_decay: float = 0.2,
    quantity_decay: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate orders and order lines matching the internal database schema.

    Each customer receives at most one generated order. Every order line gets
    a random product. Line counts and quantities range from 1 to their
    respective maximums, with a steep probability bias toward 1.
    """
    if num_orders < 0:
        raise ValueError("num_orders must not be negative")
    if max_order_lines < 1:
        raise ValueError("max_order_lines must be at least 1")
    if max_quantity < 1:
        raise ValueError("max_quantity must be at least 1")
    if not 0 <= line_count_decay <= 1:
        raise ValueError("line_count_decay must be between 0 and 1")
    if not 0 <= quantity_decay <= 1:
        raise ValueError("quantity_decay must be between 0 and 1")
    start_datetime = (
        starttime
        if isinstance(starttime, datetime)
        else datetime.combine(starttime, time.min)
    )
    end_datetime = (
        endtime
        if isinstance(endtime, datetime)
        else datetime.combine(endtime, time.max)
    )
    if start_datetime > end_datetime:
        raise ValueError("starttime must not be after endtime")

    required_customer_columns = {"customer_id", "address"}
    missing_customer_columns = required_customer_columns - set(customer_table.columns)
    if missing_customer_columns:
        raise KeyError(
            "customer_table is missing required columns: "
            + ", ".join(sorted(missing_customer_columns))
        )

    required_product_columns = {"product_id", "current_price"}
    missing_product_columns = required_product_columns - set(product_table.columns)
    if missing_product_columns:
        raise KeyError(
            "product_table is missing required columns: "
            + ", ".join(sorted(missing_product_columns))
        )
    if num_orders and customer_table.empty:
        raise ValueError("customer_table must contain customers to place orders")
    if num_orders > len(customer_table):
        raise ValueError(
            "num_orders cannot exceed the number of available customers"
        )
    if num_orders and product_table.empty:
        raise ValueError("product_table must contain products for order lines")

    customers = random.sample(
        customer_table.to_dict(orient="records"),
        k=num_orders,
    )
    products = product_table.to_dict(orient="records")
    duration_microseconds = (end_datetime - start_datetime) // timedelta(
        microseconds=1
    )

    orders = []
    order_lines = []
    for order_offset, customer in enumerate(customers, start=1):
        order_id = current_max_order_id + order_offset
        order_date = start_datetime + timedelta(
            microseconds=random.randint(0, duration_microseconds)
        )
        orders.append(
            {
                "order_id": order_id,
                "customer_id": customer["customer_id"],
                "address": customer["address"],
                "order_date": order_date,
            }
        )

        for _ in range(_skewed_random_int(max_order_lines, line_count_decay)):
            product = random.choice(products)
            order_lines.append(
                {
                    "order_line_id": (
                        current_max_order_line_id + len(order_lines) + 1
                    ),
                    "order_id": order_id,
                    "product_id": product["product_id"],
                    "quantity": _skewed_random_int(max_quantity, quantity_decay),
                    "price": product["current_price"],
                }
            )

    return (
        pd.DataFrame(
            orders,
            columns=["order_id", "customer_id", "address", "order_date"],
        ),
        pd.DataFrame(
            order_lines,
            columns=[
                "order_line_id",
                "order_id",
                "product_id",
                "quantity",
                "price",
            ],
        ),
    )
