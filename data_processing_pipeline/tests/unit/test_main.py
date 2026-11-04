from types import SimpleNamespace
from unittest.mock import sentinel

from app import main as pipeline_main


def test_main_logs_pipeline_startup_and_initialization_decisions(
    monkeypatch, caplog
):
    config = SimpleNamespace(
        historical_orders=SimpleNamespace(
            days=sentinel.days,
            orders_per_day=sentinel.orders_per_day,
        ),
        continuous_orders=SimpleNamespace(
            interval_seconds=sentinel.interval_seconds,
            orders_per_interval=sentinel.orders_per_interval,
        ),
        repeat_customer_probability=sentinel.repeat_customer_probability,
        generation=sentinel.generation,
    )
    past_orders = []
    continuous_orders = []
    monkeypatch.setattr(pipeline_main, "load_config", lambda _: config)
    monkeypatch.setattr(pipeline_main, "table_has_records", lambda **kwargs: False)
    monkeypatch.setattr(pipeline_main, "process_products", lambda: None)
    monkeypatch.setattr(
        pipeline_main,
        "process_past_orders",
        lambda **kwargs: past_orders.append(kwargs),
    )
    monkeypatch.setattr(
        pipeline_main,
        "process_orders_contineously",
        lambda **kwargs: continuous_orders.append(kwargs),
    )

    caplog.set_level("INFO", logger=pipeline_main.__name__)

    pipeline_main.main()

    assert past_orders == [
        {
            "days": sentinel.days,
            "orders_per_day": sentinel.orders_per_day,
            "chance_of_repeat_customer": sentinel.repeat_customer_probability,
            "generation_config": sentinel.generation,
        }
    ]
    assert continuous_orders == [
        {
            "timecycle_seconds": sentinel.interval_seconds,
            "order_per_timecycle": sentinel.orders_per_interval,
            "chance_of_repeat_customer": sentinel.repeat_customer_probability,
            "generation_config": sentinel.generation,
        }
    ]
    assert "Starting ETL pipeline" in caplog.text
    assert "Product data is missing; loading product catalog" in caplog.text
    assert "Order history is missing; generating historical orders" in caplog.text
    assert "Starting continuous order processing" in caplog.text
