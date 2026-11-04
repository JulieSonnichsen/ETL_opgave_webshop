from datetime import datetime, timedelta
import logging
import time
from app.config import OrderGenerationConfig
from app.flows.process_orders import process_orders


logger = logging.getLogger(__name__)


def process_orders_contineously(
    timecycle_seconds: int,
    order_per_timecycle: int,
    chance_of_repeat_customer: float,
    generation_config: OrderGenerationConfig,
):
    """Process order batches forever, waiting one time cycle between batches."""
    logger.info(
        "Continuous order processing configured for %d orders every %d seconds",
        order_per_timecycle,
        timecycle_seconds,
    )
    while True:
        logger.info("Waiting %d seconds before the next order batch", timecycle_seconds)
        time.sleep(timecycle_seconds)
        starttime = datetime.now() - timedelta(seconds=timecycle_seconds)
        endtime = datetime.now()


        process_orders(
            starttime=starttime,
            endtime=endtime,
            num_orders=order_per_timecycle,
            chance_of_repeat_customer=chance_of_repeat_customer,
            generation_config=generation_config,
        )