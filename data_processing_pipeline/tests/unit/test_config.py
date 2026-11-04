import pytest

from app.config import (
    ContinuousOrderConfig,
    HistoricalOrderConfig,
    OrderGenerationConfig,
    PipelineConfig,
    load_config,
)


def test_load_config_reads_and_validates_pipeline_sections():
    config = load_config()

    assert isinstance(config, PipelineConfig)
    assert isinstance(config.historical_orders, HistoricalOrderConfig)
    assert isinstance(config.continuous_orders, ContinuousOrderConfig)
    assert isinstance(config.generation, OrderGenerationConfig)
    assert 0 <= config.repeat_customer_probability <= 1
    assert 0 <= config.generation.new_address_probability <= 1
    assert 0 <= config.generation.new_price_probability <= 1
    assert config.generation.max_order_lines >= 1
    assert config.generation.max_quantity >= 1


def test_load_config_rejects_non_mapping_configuration(tmp_path):
    config_path = tmp_path / "config.yml"
    config_path.write_text("- not a mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="must be a YAML mapping"):
        load_config(config_path)
