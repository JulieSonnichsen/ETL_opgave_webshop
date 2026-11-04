import json
import random

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.cli import build_parser
from app.fault_engine import FaultEngine
from app.faults import Fault, register_fault
from app.faults import delay as delay_faults
from app.faults.data import MALFORMED_JSON_HANDLERS


PRODUCT = {
    "name": "Phone",
    "specifications": [{"name": "memory", "value": "16GB"}],
}


def create_client(mode: str, fault_options=None) -> TestClient:
    app = FastAPI()
    app.add_middleware(
        FaultEngine,
        mode=mode,
        fault_options=fault_options,
    )

    @app.get("/product")
    async def get_product():
        return PRODUCT

    @app.get("/products")
    async def get_products():
        return [PRODUCT, {"name": "Tablet"}]

    @app.get("/text")
    async def get_text():
        return "unchanged"

    return TestClient(app)


def test_normal_mode_preserves_json_response():
    response = create_client("normal").get("/product")

    assert response.status_code == 200
    assert response.json() == PRODUCT


def test_random_mode_uses_normal_behavior_when_fault_probability_is_zero(
    monkeypatch,
):
    monkeypatch.setattr(random, "random", lambda: 0.0)

    response = create_client(
        "random",
        fault_options={"random": {"fault_probability": 0}},
    ).get("/product")

    assert response.status_code == 200
    assert response.json() == PRODUCT


def test_random_mode_selects_a_fault_when_fault_probability_is_one(
    monkeypatch,
):
    monkeypatch.setattr(random, "random", lambda: 0.0)
    monkeypatch.setattr(random, "choice", lambda modes: "service_unavailable")

    response = create_client(
        "random",
        fault_options={
            "random": {"fault_probability": 1},
            "service_unavailable": {"probability": 1},
        },
    ).get("/product")

    assert response.status_code == 503


def test_random_mode_rejects_invalid_fault_probability():
    with pytest.raises(ValueError, match="between 0 and 1"):
        FaultEngine(
            FastAPI(),
            mode="random",
            fault_options={"random": {"fault_probability": 1.1}},
        )


def test_missing_values_mode_replaces_a_random_subset_with_null(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 1.0)
    monkeypatch.setattr(random, "choice", lambda paths: paths[-1])

    response = create_client("missing_values").get("/product")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Phone",
        "specifications": [{"name": "memory", "value": None}],
    }


def test_missing_fields_mode_removes_random_fields(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 1.0)
    monkeypatch.setattr(random, "choice", lambda paths: paths[-1])

    response = create_client("missing_fields").get("/product")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Phone",
        "specifications": [{"name": "memory"}],
    }


def test_missing_fields_probability_zero_preserves_fields():
    response = create_client(
        "missing_fields",
        fault_options={"missing_fields": {"probability": 0}},
    ).get("/product")

    assert response.status_code == 200
    assert response.json() == PRODUCT


def test_missing_fields_probability_one_removes_every_field():
    response = create_client(
        "missing_fields",
        fault_options={"missing_fields": {"probability": 1}},
    ).get("/product")

    assert response.status_code == 200
    assert response.json() == {}


def test_missing_values_probability_zero_preserves_values():
    response = create_client(
        "missing_values",
        fault_options={"missing_values": {"probability": 0}},
    ).get("/product")

    assert response.status_code == 200
    assert response.json() == PRODUCT


def test_missing_values_rejects_probability_outside_zero_to_one():
    with pytest.raises(ValueError, match="between 0 and 1"):
        create_client(
            "missing_values",
            fault_options={"missing_values": {"probability": 1.1}},
        ).get("/product")


@pytest.mark.parametrize(
    "handler",
    MALFORMED_JSON_HANDLERS,
    ids=[
        "unmatched-brace",
        "trailing-comma",
        "invalid-token",
        "unclosed-array",
    ],
)
def test_malformed_json_mode_randomly_uses_invalid_encodings(
    monkeypatch,
    handler,
):
    monkeypatch.setattr(random, "choice", lambda handlers: handler)

    response = create_client("malformed_json").get("/product")

    assert response.status_code == 200
    assert int(response.headers["content-length"]) == len(response.content)
    with pytest.raises(json.JSONDecodeError):
        response.json()


def test_fault_modes_leave_non_json_responses_unchanged():
    response = create_client("malformed_json").get("/text")

    assert response.status_code == 200
    assert response.text == "unchanged"


def test_delay_mode_sleeps_for_a_random_duration_without_changing_response(
    monkeypatch,
):
    observed_delays = []
    observed_bounds = []

    async def record_sleep(delay_seconds):
        observed_delays.append(delay_seconds)

    def choose_delay(minimum, maximum):
        observed_bounds.append((minimum, maximum))
        return 0.75

    monkeypatch.setattr(delay_faults.asyncio, "sleep", record_sleep)
    monkeypatch.setattr(delay_faults.random, "uniform", choose_delay)

    response = create_client(
        "delay",
        fault_options={
            "delay": {
                "delay_min_seconds": 0.1,
                "delay_max_seconds": 2.0,
            }
        },
    ).get("/text")

    assert response.status_code == 200
    assert response.text == "unchanged"
    assert observed_delays == [0.75]
    assert observed_bounds == [(0.1, 2.0)]


def test_service_unavailable_mode_returns_503_without_calling_endpoint():
    response = create_client("service_unavailable").get("/product")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service temporarily unavailable"}


def test_network_fault_probability_zero_calls_endpoint():
    response = create_client(
        "service_unavailable",
        fault_options={"service_unavailable": {"probability": 0}},
    ).get("/product")

    assert response.status_code == 200
    assert response.json() == PRODUCT


def test_network_fault_probability_one_returns_error(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.0)

    response = create_client(
        "service_unavailable",
        fault_options={"service_unavailable": {"probability": 1}},
    ).get("/product")

    assert response.status_code == 503


def test_wrong_data_mode_returns_valid_json_with_wrong_scalar_types(
    monkeypatch,
):
    monkeypatch.setattr(random, "random", lambda: 0.0)
    monkeypatch.setattr(random, "choice", lambda paths: paths[-1])

    response = create_client(
        "wrong_data",
        fault_options={"wrong_data": {"probability": 1}},
    ).get("/product")

    assert response.status_code == 200
    assert response.json() == {
        "name": 0,
        "specifications": [
            {"name": 0, "value": 0},
        ],
    }


def test_record_modes_drop_or_duplicate_top_level_list_items(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 1.0)
    monkeypatch.setattr(random, "choice", lambda paths: paths[-1])

    dropped = create_client(
        "drop_records",
        fault_options={"drop_records": {"probability": 1}},
    ).get("/products")
    duplicated = create_client(
        "duplicate_records",
        fault_options={"duplicate_records": {"probability": 1}},
    ).get("/products")

    assert dropped.json() == [PRODUCT]
    assert duplicated.json() == [PRODUCT, {"name": "Tablet"}, {"name": "Tablet"}]


def test_empty_response_mode_returns_empty_top_level_list():
    response = create_client("empty_response").get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_rate_limit_mode_returns_retry_after_header(monkeypatch):
    monkeypatch.setattr(random, "randint", lambda minimum, maximum: 3)

    response = create_client("rate_limit").get("/product")

    assert response.status_code == 429
    assert response.headers["retry-after"] == "3"
    assert response.json() == {"detail": "Rate limit exceeded"}


@pytest.mark.parametrize("status_code", [502, 503, 504])
def test_gateway_error_mode_returns_a_random_gateway_status(
    monkeypatch,
    status_code,
):
    monkeypatch.setattr(random, "choice", lambda statuses: status_code)

    response = create_client("gateway_error").get("/product")

    assert response.status_code == status_code
    assert response.json() == {"detail": "Simulated gateway error"}


def test_truncated_response_mode_returns_incomplete_body(monkeypatch):
    monkeypatch.setattr(random, "randint", lambda minimum, maximum: 10)

    response = create_client("truncated_response").get("/product")

    assert response.status_code == 200
    assert len(response.content) == 10
    assert int(response.headers["content-length"]) > len(response.content)
    with pytest.raises(json.JSONDecodeError):
        response.json()


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(float("nan"), 1.0), (0.0, float("inf")), (-0.1, 1.0), (2.0, 1.0)],
)
def test_delay_mode_rejects_invalid_delay_bounds(minimum, maximum):
    with pytest.raises(ValueError, match="Delay bounds"):
        FaultEngine(
            FastAPI(),
            mode="delay",
            fault_options={
                "delay": {
                    "delay_min_seconds": minimum,
                    "delay_max_seconds": maximum,
                }
            },
        )


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="Unknown fault mode"):
        FaultEngine(FastAPI(), mode="unregistered")


def test_cli_defaults_to_normal_and_parses_fault_options():
    parser = build_parser()

    defaults = parser.parse_args([])
    arguments = parser.parse_args(
        [
            "--fault-mode",
            "missing_fields",
            "--missing-fields-probability",
            "0.7",
            "--failure-probability",
            "0.2",
            "--wrong-data-probability",
            "0.4",
            "--drop-records-probability",
            "0.5",
            "--duplicate-records-probability",
            "0.6",
            "--random-fault-probability",
            "0.25",
        ]
    )

    assert defaults.fault_mode == "normal"
    assert arguments.fault_mode == "missing_fields"
    assert arguments.missing_fields_probability == 0.7
    assert arguments.failure_probability == 0.2
    assert arguments.wrong_data_probability == 0.4
    assert arguments.drop_records_probability == 0.5
    assert arguments.duplicate_records_probability == 0.6
    assert arguments.random_fault_probability == 0.25


def test_registered_fault_plugin_is_delegated_to():
    @register_fault("test_plugin")
    class TestFault(Fault):
        async def apply(
            self,
            request: Request,
            call_next: RequestResponseEndpoint,
        ) -> Response:
            return JSONResponse({"plugin": "active"})

    response = create_client("test_plugin").get("/product")

    assert response.status_code == 200
    assert response.json() == {"plugin": "active"}
