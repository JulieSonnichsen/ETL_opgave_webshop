import argparse

import uvicorn

from app.faults import registered_faults
from app.main import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Product API.")
    parser.add_argument(
        "--fault-mode",
        choices=registered_faults(),
        default="normal",
        help="Fault plugin to enable (default: normal).",
    )
    parser.add_argument(
        "--delay-min-seconds",
        type=float,
        default=0.1,
        help="Minimum delay for --fault-mode delay (default: 0.1).",
    )
    parser.add_argument(
        "--delay-max-seconds",
        type=float,
        default=2.0,
        help="Maximum delay for --fault-mode delay (default: 2.0).",
    )
    parser.add_argument(
        "--missing-values-probability",
        type=float,
        default=0.35,
        help="Value-removal probability for missing_values (default: 0.35).",
    )
    parser.add_argument(
        "--missing-fields-probability",
        type=float,
        default=0.35,
        help="Field-removal probability for missing_fields (default: 0.35).",
    )
    parser.add_argument(
        "--failure-probability",
        type=float,
        default=1.0,
        help=(
            "Probability of returning an error for network fault modes "
            "(default: 1.0)."
        ),
    )
    parser.add_argument(
        "--wrong-data-probability",
        type=float,
        default=0.35,
        help="Probability of corrupting each JSON scalar (default: 0.35).",
    )
    parser.add_argument(
        "--drop-records-probability",
        type=float,
        default=0.35,
        help="Probability of dropping each top-level list record (default: 0.35).",
    )
    parser.add_argument(
        "--duplicate-records-probability",
        type=float,
        default=0.35,
        help=(
            "Probability of duplicating each top-level list record "
            "(default: 0.35)."
        ),
    )
    parser.add_argument(
        "--random-fault-probability",
        type=float,
        default=0.5,
        help=(
            "Probability random mode applies a fault instead of normal "
            "behavior (default: 0.5)."
        ),
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind (default: 0.0.0.0).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    arguments = parser.parse_args()
    fault_options = {
        "delay": {
            "delay_min_seconds": arguments.delay_min_seconds,
            "delay_max_seconds": arguments.delay_max_seconds,
        },
        "missing_values": {
            "probability": arguments.missing_values_probability,
        },
        "missing_fields": {
            "probability": arguments.missing_fields_probability,
        },
        "service_unavailable": {
            "probability": arguments.failure_probability,
        },
        "rate_limit": {
            "probability": arguments.failure_probability,
        },
        "gateway_error": {
            "probability": arguments.failure_probability,
        },
        "wrong_data": {
            "probability": arguments.wrong_data_probability,
        },
        "drop_records": {
            "probability": arguments.drop_records_probability,
        },
        "duplicate_records": {
            "probability": arguments.duplicate_records_probability,
        },
        "random": {
            "fault_probability": arguments.random_fault_probability,
        },
    }

    try:
        application = create_app(
            fault_mode=arguments.fault_mode,
            fault_options=fault_options,
        )
    except ValueError as error:
        parser.error(str(error))

    uvicorn.run(application, host=arguments.host, port=arguments.port)


if __name__ == "__main__":
    main()
