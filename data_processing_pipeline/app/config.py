from dataclasses import dataclass
import math
from pathlib import Path

import yaml


@dataclass(frozen=True)
class HistoricalOrderConfig:
    days: int
    orders_per_day: int


@dataclass(frozen=True)
class ContinuousOrderConfig:
    interval_seconds: int
    orders_per_interval: int


@dataclass(frozen=True)
class OrderGenerationConfig:
    new_address_probability: float
    new_price_probability: float
    max_price_change_percent: float
    max_order_lines: int
    max_quantity: int
    line_count_decay: float
    quantity_decay: float


@dataclass(frozen=True)
class PipelineConfig:
    historical_orders: HistoricalOrderConfig
    continuous_orders: ContinuousOrderConfig
    repeat_customer_probability: float
    generation: OrderGenerationConfig


def _section(config: dict, name: str) -> dict:
    section = config.get(name)
    if not isinstance(section, dict):
        raise ValueError(f"Configuration section '{name}' must be a mapping")
    return section


def _integer(section: dict, name: str, *, minimum: int) -> int:
    value = section.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(
            f"Configuration value '{name}' must be an integer >= {minimum}"
        )
    return value


def _number(
    section: dict,
    name: str,
    *,
    minimum: float,
    maximum: float,
) -> float:
    value = section.get(name)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not minimum <= value <= maximum
    ):
        raise ValueError(
            f"Configuration value '{name}' must be between "
            f"{minimum} and {maximum}"
        )
    return float(value)


def load_config(config_path: str | Path | None = None) -> PipelineConfig:
    """Load and validate pipeline settings from the YAML configuration file."""
    path = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).resolve().parent.parent / "config.yml"
    )
    with path.open(encoding="utf-8") as config_file:
        raw_config = yaml.safe_load(config_file)
    if not isinstance(raw_config, dict):
        raise ValueError("Pipeline configuration must be a YAML mapping")

    orders = _section(raw_config, "orders")
    historical = _section(orders, "historical")
    continuous = _section(orders, "continuous")
    generation = _section(raw_config, "generation")

    return PipelineConfig(
        historical_orders=HistoricalOrderConfig(
            days=_integer(historical, "days", minimum=1),
            orders_per_day=_integer(historical, "orders_per_day", minimum=0),
        ),
        continuous_orders=ContinuousOrderConfig(
            interval_seconds=_integer(
                continuous,
                "interval_seconds",
                minimum=1,
            ),
            orders_per_interval=_integer(
                continuous,
                "orders_per_interval",
                minimum=0,
            ),
        ),
        repeat_customer_probability=_number(
            orders,
            "repeat_customer_probability",
            minimum=0,
            maximum=1,
        ),
        generation=OrderGenerationConfig(
            new_address_probability=_number(
                generation,
                "new_address_probability",
                minimum=0,
                maximum=1,
            ),
            new_price_probability=_number(
                generation,
                "new_price_probability",
                minimum=0,
                maximum=1,
            ),
            max_price_change_percent=_number(
                generation,
                "max_price_change_percent",
                minimum=0,
                maximum=100,
            ),
            max_order_lines=_integer(
                generation,
                "max_order_lines",
                minimum=1,
            ),
            max_quantity=_integer(generation, "max_quantity", minimum=1),
            line_count_decay=_number(
                generation,
                "line_count_decay",
                minimum=0,
                maximum=1,
            ),
            quantity_decay=_number(
                generation,
                "quantity_decay",
                minimum=0,
                maximum=1,
            ),
        ),
    )
