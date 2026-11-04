import logging

from app.etl.extract.csv import read_csv_file

from app.etl.transform.dataframe_utils import combine_tables, add_column_with_value, pull_columns_to_table, map_columns, give_ids, shuffle_table, remove_duplicate_by_composite_columns, remove_columns, remove_null_records
from app.etl.generate.products import generate_prices
from app.etl.load.postgres import load_table_into_postgres

from app.db.db_connector import get_dbconnector


logger = logging.getLogger(__name__)


def process_products():
    """Extract product CSVs, normalize the catalog, and load it into both databases."""
    logger.info("Extracting products from laptops.csv, tablets.csv, and smartphones.csv")
    # EXTRACT
    # -------------------------------------------------------------------------------------------------

    # extract product tables
    laptops = read_csv_file(path="data/laptops.csv", encoding="cp1252")
    tablets = read_csv_file(path="data/tablets.csv", encoding="utf-8")
    phones = read_csv_file(path="data/smartphones.csv", encoding="utf-8")

    logger.info(
        "Extracted %d laptops, %d tablets, and %d phones",
        len(laptops),
        len(tablets),
        len(phones),
    )

    # -------------------------------------------------------------------------------------------------


    # TRANSFORM
    # -------------------------------------------------------------------------------------------------

    # map product tables
    
    laptop_map = {
        "Company": "manufactorer",
        "Product": "model_name",
        "Inches": "screen_size",
        "ScreenResolution": "screen_resolution",
        "Cpu": "processor",
        "Gpu": "gpu",
        "Ram": "ram",
        "Memory": "memory",
        "OpSys": "operating_system",
        "Weight": "weight"
    }
    tablet_map = {
        "name": "model_name",
        "brand": "manufactorer",
        "ram": "ram",
        "memory_inbuilt": "memory",
        "battery_capacity": "battery_capacity",
        "display_size_inches": "screen_size",
        "pixel": "screen_resolution",
        "primary_front_camera": "front_camera_mp",
        "primary_rear_camera": "camera_mp"
    }
    phone_map = {
        "brand_name": "manufactorer",
        "model": "model_name",
        "screen_size": "screen_size",
        "operating_system": "operating_system",
        "battery_capacity": "battery_capacity",
        "ram": "ram",
        "storage": "memory",
        "camera_mp": "camera_mp",
        "front_camera_mp": "front_camera_mp",
        "weight": "weight",
        "thickness": "thickness",
        "chipset": "processor",
        "gpu": "gpu"}

    laptops = map_columns(table=laptops, column_mapping=laptop_map)
    tablets = map_columns(table=tablets, column_mapping=tablet_map)
    phones = map_columns(table=phones, column_mapping=phone_map)

    # add category column to product tables

    laptops = add_column_with_value(table=laptops, column_name="category", value="laptop")
    tablets = add_column_with_value(table=tablets, column_name="category", value="tablet")
    phones = add_column_with_value(table=phones, column_name="category", value="phone")

    # combine product tables

    products = combine_tables(tables=[laptops, tablets, phones])

    # remove duplicates

    extracted_product_count = len(products)
    products = remove_duplicate_by_composite_columns(table=products, composite_columns=["manufactorer", "model_name"])
    logger.info(
        "Combined %d products and removed %d duplicates; %d products remain",
        extracted_product_count,
        extracted_product_count - len(products),
        len(products),
    )

    # shuffle

    products = shuffle_table(table=products)


    # give ids

    products = give_ids(table=products, id_column_name="product_id")


    # build relational tables

    products, product_specifications, specifications = pull_columns_to_table(
        table=products,
        columns_to_keep=["product_id", "manufactorer", "model_name", "category"],
        id_column="product_id"
    )

    # rename columns

    product_specifications = map_columns(
        table=product_specifications,
        column_mapping={
            "record_id": "product_id",
            "column_id": "specification_id",
            "value": "value"
        }
    )

    product_specifications = remove_null_records(table=product_specifications, column="value")

    product_specifications = give_ids(table=product_specifications, id_column_name="product_specification_id")

    specifications = map_columns(table=specifications, column_mapping={
        "id": "specification_id",
        "name": "specification_name"
    })


    # shuffle

    products_for_internal_db = shuffle_table(table=products)


    # give ids

    products_for_internal_db = give_ids(
        table=products_for_internal_db,
        id_column_name="product_id",
    )

    # give prices

    products_for_internal_db = generate_prices(table=products_for_internal_db, column_name="current_price", floor=150.00, ceiling=1500.00)

    logger.info(
        "Prepared %d products, %d specifications, and %d product specifications",
        len(products),
        len(specifications),
        len(product_specifications),
    )



    # -------------------------------------------------------------------------------------------------


    # LOAD
    # -------------------------------------------------------------------------------------------------

    # load to api db

    load_table_into_postgres(db_name="api_db", table_name="products", table=products)
    load_table_into_postgres(db_name="api_db", table_name="specifications", table=specifications)
    load_table_into_postgres(db_name="api_db", table_name="product_specifications", table=product_specifications)

    # load to internal db
    load_table_into_postgres(db_name="internal_db", table_name="products", table=products_for_internal_db)

    # commit queries atomically
    db_connector = get_dbconnector()

    db_connector.commit_queries(db_name="api_db")
    db_connector.commit_queries(db_name="internal_db")

    logger.info("Product catalog loaded into api_db and internal_db")

    # -------------------------------------------------------------------------------------------------
