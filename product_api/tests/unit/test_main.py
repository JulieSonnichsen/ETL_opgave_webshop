from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app


def test_get_products_includes_specifications_and_products_without_them(
    monkeypatch,
):
    monkeypatch.setenv("API_DB", "api_db")
    monkeypatch.setenv("API_DB_USERNAME", "admin")
    monkeypatch.setenv("API_DB_PASSWORD", "password")
    monkeypatch.setenv("API_DB_HOST", "localhost")
    monkeypatch.setenv("API_DB_PORT", "5432")

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchall.return_value = [
        (1, "Acme", "Laptop A", "laptop", "memory", "16GB"),
        (1, "Acme", "Laptop A", "laptop", "storage", "512GB"),
        (2, "Widget Co", "Phone B", "phone", None, None),
    ]
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr("app.routes.products.psycopg.connect", connect)

    response = TestClient(app).get("/products")

    assert response.status_code == 200
    assert response.json() == [
        {
            "manufactorer": "Acme",
            "model_name": "Laptop A",
            "category": "laptop",
            "specifications": [
                {"name": "memory", "value": "16GB"},
                {"name": "storage", "value": "512GB"},
            ],
        },
        {
            "manufactorer": "Widget Co",
            "model_name": "Phone B",
            "category": "phone",
            "specifications": [],
        },
    ]
    connect.assert_called_once_with(
        dbname="api_db",
        user="admin",
        password="password",
        host="localhost",
        port=5432,
    )


def test_get_products_filters_by_product_fields_and_specification(monkeypatch):
    monkeypatch.setenv("API_DB", "api_db")
    monkeypatch.setenv("API_DB_USERNAME", "admin")
    monkeypatch.setenv("API_DB_PASSWORD", "password")
    monkeypatch.setenv("API_DB_HOST", "localhost")
    monkeypatch.setenv("API_DB_PORT", "5432")

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchall.return_value = [
        (1, "Acme", "Laptop A", "laptop", "memory", "16GB"),
    ]
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr("app.routes.products.psycopg.connect", connect)

    response = TestClient(app).get(
        "/products",
        params={
            "category": "laptop",
            "manufacturer": "Acme",
            "model_name": "Laptop A",
            "specification": "memory",
            "value": "16GB",
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "manufactorer": "Acme",
            "model_name": "Laptop A",
            "category": "laptop",
            "specifications": [{"name": "memory", "value": "16GB"}],
        }
    ]
    query, parameters = connection.execute.call_args.args
    assert "LOWER(p.category) = LOWER(%s)" in query
    assert "LOWER(p.manufactorer) = LOWER(%s)" in query
    assert "LOWER(p.model_name) = LOWER(%s)" in query
    assert "LOWER(filter_s.specification_name) = LOWER(%s)" in query
    assert "LOWER(filter_ps.value) = LOWER(%s)" in query
    assert parameters == ("laptop", "Acme", "Laptop A", "memory", "16GB")


def test_get_specifications_filters_by_name_and_categories(monkeypatch):
    monkeypatch.setenv("API_DB", "api_db")
    monkeypatch.setenv("API_DB_USERNAME", "admin")
    monkeypatch.setenv("API_DB_PASSWORD", "password")
    monkeypatch.setenv("API_DB_HOST", "localhost")
    monkeypatch.setenv("API_DB_PORT", "5432")

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.execute.return_value.fetchall.return_value = [
        ("memory", ["8GB", "16GB"], ["laptop"]),
    ]
    connect = MagicMock(return_value=connection)
    monkeypatch.setattr("app.routes.specifications.psycopg.connect", connect)

    response = TestClient(app).get(
        "/specifications",
        params=[("name", "memory"), ("categories", "LAPTOP")],
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "memory",
            "values": ["8GB", "16GB"],
            "categories": ["laptop"],
        }
    ]
    query, parameters = connection.execute.call_args.args
    assert "LOWER(s.specification_name) = LOWER(%s)" in query
    assert "LOWER(p.category) = ANY(%s)" in query
    assert parameters == ("memory", ["laptop"])
