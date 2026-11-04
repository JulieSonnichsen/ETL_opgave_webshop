import logging
from pathlib import Path

from app.config import load_config
from app.flows.process_products import process_products
from app.flows.process_past_orders import process_past_orders
from app.flows.process_orders_contineously import process_orders_contineously
from app.etl.extract.postgres import table_has_records


logger = logging.getLogger(__name__)


def main(config_path: str | Path | None = None) -> None:
    """Initialize missing product/order data, then process orders continuously."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Starting ETL pipeline")
    config = load_config(config_path)

    logger.info("Checking whether product tables need initialization")
    if not table_has_records(db_name="internal_db", table_name="products") or not table_has_records(db_name="api_db", table_name="products"):
        logger.info("Product data is missing; loading product catalog")
        process_products()
    else:
        logger.info("Product tables are already populated; skipping product load")

    logger.info("Checking whether order history needs initialization")
    if not table_has_records(db_name="internal_db", table_name="orders"):
        logger.info("Order history is missing; generating historical orders")
        process_past_orders(
            days=config.historical_orders.days,
            orders_per_day=config.historical_orders.orders_per_day,
            chance_of_repeat_customer=config.repeat_customer_probability,
            generation_config=config.generation,
        )
    else:
        logger.info("Order history is already populated; skipping historical load")

    logger.info("Starting continuous order processing")
    process_orders_contineously(
        timecycle_seconds=config.continuous_orders.interval_seconds,
        order_per_timecycle=config.continuous_orders.orders_per_interval,
        chance_of_repeat_customer=config.repeat_customer_probability,
        generation_config=config.generation,
    )


if __name__ == "__main__":
    main()
