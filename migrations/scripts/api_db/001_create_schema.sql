CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    manufactorer TEXT,
    model_name TEXT,
    category TEXT
);

CREATE TABLE specifications (
    specification_id INTEGER PRIMARY KEY,
    specification_name TEXT NOT NULL UNIQUE
);

CREATE TABLE product_specifications (
    product_specification_id INTEGER  PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products (product_id),
    specification_id INTEGER NOT NULL
        REFERENCES specifications (specification_id),
    value TEXT,
    UNIQUE (product_id, specification_id)
);

CREATE INDEX idx_product_specifications_product_id
    ON product_specifications (product_id);
CREATE INDEX idx_product_specifications_specification_id
    ON product_specifications (specification_id);
