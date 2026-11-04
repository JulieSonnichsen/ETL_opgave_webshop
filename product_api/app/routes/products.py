import os

import psycopg
from fastapi import APIRouter

from ..schemas import Product, ProductSpecification


router = APIRouter()


@router.get("/products", response_model=list[Product])
def get_products(
    category: str | None = None,
    manufacturer: str | None = None,
    model_name: str | None = None,
    specification: str | None = None,
    value: str | None = None,
) -> list[Product]:
    """Return products matching the supplied filters, with all their specs."""
    conditions = []
    parameters = []
    for column, filter_value in (
        ("p.category", category),
        ("p.manufactorer", manufacturer),
        ("p.model_name", model_name),
    ):
        if filter_value is not None:
            conditions.append(f"LOWER({column}) = LOWER(%s)")
            parameters.append(filter_value)

    specification_conditions = []
    if specification is not None:
        specification_conditions.append(
            "LOWER(filter_s.specification_name) = LOWER(%s)"
        )
        parameters.append(specification)
    if value is not None:
        specification_conditions.append("LOWER(filter_ps.value) = LOWER(%s)")
        parameters.append(value)
    if specification_conditions:
        conditions.append(
            "EXISTS ("
            "SELECT 1 FROM product_specifications AS filter_ps "
            "JOIN specifications AS filter_s "
            "ON filter_s.specification_id = filter_ps.specification_id "
            "WHERE filter_ps.product_id = p.product_id AND "
            + " AND ".join(specification_conditions)
            + ")"
        )

    where_clause = (
        "WHERE " + " AND ".join(conditions) if conditions else ""
    )
    with psycopg.connect(
        dbname=os.environ["API_DB"],
        user=os.environ["API_DB_USERNAME"],
        password=os.environ["API_DB_PASSWORD"],
        host=os.environ["API_DB_HOST"],
        port=int(os.environ["API_DB_PORT"]),
    ) as connection:
        rows = connection.execute(
            f"""
            SELECT
                p.product_id,
                p.manufactorer,
                p.model_name,
                p.category,
                s.specification_name,
                ps.value
            FROM products AS p
            LEFT JOIN product_specifications AS ps
                ON ps.product_id = p.product_id
            LEFT JOIN specifications AS s
                ON s.specification_id = ps.specification_id
            {where_clause}
            ORDER BY p.product_id, s.specification_name
            """,
            tuple(parameters),
        ).fetchall()

    products: dict[int, Product] = {}
    for (
        product_id,
        manufactorer,
        model_name,
        category,
        specification_name,
        value,
    ) in rows:
        product = products.setdefault(
            product_id,
            Product(
                manufactorer=manufactorer,
                model_name=model_name,
                category=category,
                specifications=[],
            ),
        )
        if specification_name is not None:
            product.specifications.append(
                ProductSpecification(name=specification_name, value=value)
            )

    return list(products.values())
