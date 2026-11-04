from datetime import datetime, timedelta
import logging
import math

from app.config import OrderGenerationConfig
from app.db.db_connector import get_dbconnector

from app.etl.extract.customers import get_customers_with_address
from app.etl.extract.postgres import get_max_id, read_table_from_postgres

from app.etl.generate.customers import generate_customers, give_new_addresses
from app.etl.generate.orders import generate_orders
from app.etl.generate.products import give_new_prices

from app.etl.transform.dataframe_utils import combine_tables, shuffle_table, remove_columns, filter_updated_records

from app.etl.load.postgres import load_table_into_postgres, update_table_in_postgres


logger = logging.getLogger(__name__)


def process_orders(
    starttime: datetime,
    endtime: datetime,
    num_orders: int,
    chance_of_repeat_customer: float,
    generation_config: OrderGenerationConfig,
):
    """Generate and persist one batch of orders within the given time range.

    Reuses eligible customers, creates new customers as needed, updates product
    prices, and commits the resulting customer, order, and product changes.
    """

    # CONFIG
    # -------------------------------------------------------------------------------------------------
    NUM_REPEAT_CUSTUMERS = math.ceil(chance_of_repeat_customer * num_orders)
    NUM_NEW_CUSTOMERS = num_orders - NUM_REPEAT_CUSTUMERS
    LATEST_ORDER_DATE = starttime - timedelta(weeks=1)

    # -------------------------------------------------------------------------------------------------

    logger.info(
        "Starting order batch for %s through %s: %d orders requested",
        starttime,
        endtime,
        num_orders,
    )

    # EXTRACT
    # -------------------------------------------------------------------------------------------------

    # get customers, if exist
    old_customers = get_customers_with_address(
        db_name="internal_db",
        customer_table_name="customers",
        order_table_name="orders",
        num_customers=NUM_REPEAT_CUSTUMERS,
        latest_order_date=LATEST_ORDER_DATE
    )

    if len(old_customers) < NUM_REPEAT_CUSTUMERS:
        NUM_NEW_CUSTOMERS = num_orders - len(old_customers)
    logger.info(
        "Found %d eligible repeat customers; will generate %d new customers",
        len(old_customers),
        NUM_NEW_CUSTOMERS,
    )

    # get products

    products = read_table_from_postgres(
        db_name="internal_db",
        table_name="products",
        columns=["product_id", "current_price"]
    )
    logger.info("Extracted %d products for order generation", len(products))

    # get max customer id

    max_customer_id = get_max_id(
        db_name="internal_db",
        table_name="customers",
        column_name="customer_id"
    )

    # get max order and orderline id

    max_order_id = get_max_id(
        db_name="internal_db",
        table_name="orders",
        column_name="order_id"
    )

    max_order_line_id = get_max_id(
        db_name="internal_db",
        table_name="order_lines",
        column_name="order_line_id"
    )

    # -------------------------------------------------------------------------------------------------



    # GENERATE
    # -------------------------------------------------------------------------------------------------

    # generate new customers

    new_customers = generate_customers(num_customers=NUM_NEW_CUSTOMERS, current_max_id=max_customer_id)

    # give new addresses

    old_customers_updated = give_new_addresses(
        customers=old_customers,
        chance_of_new_address=generation_config.new_address_probability,
    )
     
    # combine customers

    customers = combine_tables(tables=[new_customers, old_customers_updated])

    customers = shuffle_table(table=customers)

    # give new prices

    products_updated = give_new_prices(
        table=products,
        chance_of_new_price=generation_config.new_price_probability,
        max_change_percent=generation_config.max_price_change_percent,
    )

    # generate orders

    orders, order_lines = generate_orders(
        product_table=products,
        customer_table=customers,
        num_orders=num_orders,
        starttime=starttime,
        endtime=endtime,
        current_max_order_id=max_order_id,
        current_max_order_line_id=max_order_line_id,
        max_order_lines=generation_config.max_order_lines,
        max_quantity=generation_config.max_quantity,
        line_count_decay=generation_config.line_count_decay,
        quantity_decay=generation_config.quantity_decay,
    )

    # Only new customers are inserted; existing customers already exist.
    customers_to_load = remove_columns(
        table=new_customers,
        columns=["address"],
    )

    # filter updated products

    products_updated_filtered = filter_updated_records(original_table=products, updated_table=products_updated)
    logger.info(
        "Generated %d orders, %d order lines, and %d new customers; %d product prices changed",
        len(orders),
        len(order_lines),
        len(new_customers),
        len(products_updated_filtered),
    )

    # -------------------------------------------------------------------------------------------------



    # LOAD
    # -------------------------------------------------------------------------------------------------

    # Load new customers before their orders to satisfy the foreign key.
    load_table_into_postgres(
        db_name="internal_db",
        table_name="customers",
        table=customers_to_load,
    )

    # load orders, order lines
    load_table_into_postgres(
        db_name="internal_db",
        table_name="orders",
        table=orders,
    )

    load_table_into_postgres(
        db_name="internal_db",
        table_name="order_lines",
        table=order_lines,
    )

    # update prices

    update_table_in_postgres(
        db_name="internal_db",
        table_name="products",
        table = products_updated_filtered
    )

    dbconnector = get_dbconnector()

    dbconnector.commit_queries(db_name="internal_db")
    logger.info("Order batch committed to internal_db")



    # -------------------------------------------------------------------------------------------------