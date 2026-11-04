import os

import psycopg
from fastapi import APIRouter, Query

from ..schemas import SpecificationSummary


router = APIRouter()


@router.get("/specifications", response_model=list[SpecificationSummary])
def get_specifications(
    name: str | None = None,
    categories: list[str] | None = Query(default=None),
) -> list[SpecificationSummary]:
    """Return specifications with their distinct values and product categories."""
    conditions = []
    parameters = []
    if name is not None:
        conditions.append("LOWER(s.specification_name) = LOWER(%s)")
        parameters.append(name)
    if categories:
        conditions.append("LOWER(p.category) = ANY(%s)")
        parameters.append([category.lower() for category in categories])

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
                s.specification_name,
                array_agg(DISTINCT ps.value ORDER BY ps.value)
                    FILTER (WHERE ps.value IS NOT NULL) AS specification_values,
                array_agg(DISTINCT p.category ORDER BY p.category)
                    FILTER (WHERE p.category IS NOT NULL) AS categories
            FROM specifications AS s
            JOIN product_specifications AS ps
                ON ps.specification_id = s.specification_id
            JOIN products AS p
                ON p.product_id = ps.product_id
            {where_clause}
            GROUP BY s.specification_id, s.specification_name
            ORDER BY s.specification_name
            """,
            tuple(parameters),
        ).fetchall()

    return [
        SpecificationSummary(
            name=specification_name,
            values=values or [],
            categories=product_categories or [],
        )
        for specification_name, values, product_categories in rows
    ]
