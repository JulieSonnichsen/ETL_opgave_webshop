from datetime import datetime, timedelta
import logging
from app.config import OrderGenerationConfig
from app.flows.process_orders import process_orders


logger = logging.getLogger(__name__)


def process_past_orders(
    days: int,
    orders_per_day: int,
    chance_of_repeat_customer: float,
    generation_config: OrderGenerationConfig,
):
    """Generate order batches for each of the preceding ``days`` calendar days.

    Days are processed from oldest to most recent, with ``orders_per_day``
    orders generated for each day.
    """
    logger.info(
        "Generating historical orders for %d days at %d orders per day",
        days,
        orders_per_day,
    )
    for i in range(days, 0, -1):
        starttime = datetime.now() - timedelta(days=i + 1)
        endtime = datetime.now() - timedelta(days=i)

        logger.info("Processing historical order day %d of %d", days - i + 1, days)
        process_orders(
            starttime=starttime,
            endtime=endtime,
            num_orders=orders_per_day,
            chance_of_repeat_customer=chance_of_repeat_customer,
            generation_config=generation_config,
        )
    logger.info("Historical order generation complete")