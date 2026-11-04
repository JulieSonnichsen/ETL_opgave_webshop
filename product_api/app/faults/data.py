import json
import random
from collections.abc import Callable
from typing import Any

from .base import ResponseBodyFault, validate_probability
from .registry import register_fault


JsonPath = tuple[str | int, ...]
DEFAULT_FAULT_PROBABILITY = 0.35
FaultHandler = Callable[[bytes], bytes]


def _transform_json_body(
    body: bytes,
    transform: Callable[[Any], Any],
) -> bytes:
    payload = json.loads(body)
    return json.dumps(transform(payload), separators=(",", ":")).encode("utf-8")


def _collect_value_paths(value: Any, path: JsonPath = ()) -> list[JsonPath]:
    if isinstance(value, dict):
        return [
            value_path
            for key, item in value.items()
            for value_path in _collect_value_paths(item, path + (key,))
        ]
    if isinstance(value, list):
        return [
            value_path
            for index, item in enumerate(value)
            for value_path in _collect_value_paths(item, path + (index,))
        ]
    return [path] if value is not None else []


def _collect_field_paths(value: Any, path: JsonPath = ()) -> list[JsonPath]:
    if isinstance(value, dict):
        return [
            field_path
            for key, item in value.items()
            for field_path in (
                [path + (key,)]
                + _collect_field_paths(item, path + (key,))
            )
        ]
    if isinstance(value, list):
        return [
            field_path
            for index, item in enumerate(value)
            for field_path in _collect_field_paths(item, path + (index,))
        ]
    return []


def _select_random_paths(
    paths: list[JsonPath],
    probability: float,
) -> set[JsonPath]:
    selected = {
        path for path in paths if random.random() < probability
    }
    if probability > 0 and paths and not selected:
        selected.add(random.choice(paths))
    return selected


def _replace_values_at_paths(
    value: Any,
    selected_paths: set[JsonPath],
    path: JsonPath = (),
) -> Any:
    if path in selected_paths:
        return None
    if isinstance(value, dict):
        return {
            key: _replace_values_at_paths(
                item, selected_paths, path + (key,)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_values_at_paths(
                item, selected_paths, path + (index,)
            )
            for index, item in enumerate(value)
        ]
    return value


def _remove_fields_at_paths(
    value: Any,
    selected_paths: set[JsonPath],
    path: JsonPath = (),
) -> Any:
    if isinstance(value, dict):
        return {
            key: _remove_fields_at_paths(
                item, selected_paths, path + (key,)
            )
            for key, item in value.items()
            if path + (key,) not in selected_paths
        }
    if isinstance(value, list):
        return [
            _remove_fields_at_paths(
                item, selected_paths, path + (index,)
            )
            for index, item in enumerate(value)
        ]
    return value


@register_fault("missing_values")
class MissingValuesFault(ResponseBodyFault):
    def __init__(
        self,
        probability: float = DEFAULT_FAULT_PROBABILITY,
    ) -> None:
        validate_probability(probability)
        self.probability = probability

    def transform_body(self, body: bytes) -> bytes:
        def remove_random_values(value: Any) -> Any:
            paths = _collect_value_paths(value)
            return _replace_values_at_paths(
                value, _select_random_paths(paths, self.probability)
            )

        return _transform_json_body(body, remove_random_values)


@register_fault("missing_fields")
class MissingFieldsFault(ResponseBodyFault):
    def __init__(
        self,
        probability: float = DEFAULT_FAULT_PROBABILITY,
    ) -> None:
        validate_probability(probability)
        self.probability = probability

    def transform_body(self, body: bytes) -> bytes:
        def remove_random_fields(value: Any) -> Any:
            paths = _collect_field_paths(value)
            return _remove_fields_at_paths(
                value, _select_random_paths(paths, self.probability)
            )

        return _transform_json_body(body, remove_random_fields)


def _collect_scalar_paths(value: Any, path: JsonPath = ()) -> list[JsonPath]:
    if isinstance(value, dict):
        return [
            scalar_path
            for key, item in value.items()
            for scalar_path in _collect_scalar_paths(item, path + (key,))
        ]
    if isinstance(value, list):
        return [
            scalar_path
            for index, item in enumerate(value)
            for scalar_path in _collect_scalar_paths(item, path + (index,))
        ]
    return [path]


def _replace_values_at_paths_with_wrong_types(
    value: Any,
    selected_paths: set[JsonPath],
    path: JsonPath = (),
) -> Any:
    if path in selected_paths:
        if isinstance(value, str):
            return 0
        return "unexpected-type"
    if isinstance(value, dict):
        return {
            key: _replace_values_at_paths_with_wrong_types(
                item, selected_paths, path + (key,)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _replace_values_at_paths_with_wrong_types(
                item, selected_paths, path + (index,)
            )
            for index, item in enumerate(value)
        ]
    return value


@register_fault("wrong_data")
class WrongDataFault(ResponseBodyFault):
    def __init__(
        self,
        probability: float = DEFAULT_FAULT_PROBABILITY,
    ) -> None:
        validate_probability(probability)
        self.probability = probability

    def transform_body(self, body: bytes) -> bytes:
        def replace_random_values(value: Any) -> Any:
            paths = _collect_scalar_paths(value)
            selected_paths = _select_random_paths(paths, self.probability)
            return _replace_values_at_paths_with_wrong_types(
                value, selected_paths
            )

        return _transform_json_body(body, replace_random_values)


def _transform_top_level_records(
    body: bytes,
    transform: Callable[[list[Any]], list[Any]],
) -> bytes:
    def transform_records(value: Any) -> Any:
        if not isinstance(value, list):
            return value
        return transform(value)

    return _transform_json_body(body, transform_records)


@register_fault("drop_records")
class DropRecordsFault(ResponseBodyFault):
    def __init__(
        self,
        probability: float = DEFAULT_FAULT_PROBABILITY,
    ) -> None:
        validate_probability(probability)
        self.probability = probability

    def transform_body(self, body: bytes) -> bytes:
        def drop_random_records(records: list[Any]) -> list[Any]:
            paths = [(index,) for index in range(len(records))]
            selected_paths = _select_random_paths(paths, self.probability)
            return [
                record
                for index, record in enumerate(records)
                if (index,) not in selected_paths
            ]

        return _transform_top_level_records(body, drop_random_records)


@register_fault("duplicate_records")
class DuplicateRecordsFault(ResponseBodyFault):
    def __init__(
        self,
        probability: float = DEFAULT_FAULT_PROBABILITY,
    ) -> None:
        validate_probability(probability)
        self.probability = probability

    def transform_body(self, body: bytes) -> bytes:
        def duplicate_random_records(records: list[Any]) -> list[Any]:
            paths = [(index,) for index in range(len(records))]
            selected_paths = _select_random_paths(paths, self.probability)
            duplicated = []
            for index, record in enumerate(records):
                duplicated.append(record)
                if (index,) in selected_paths:
                    duplicated.append(record)
            return duplicated

        return _transform_top_level_records(body, duplicate_random_records)


@register_fault("empty_response")
class EmptyResponseFault(ResponseBodyFault):
    def transform_body(self, body: bytes) -> bytes:
        return _transform_top_level_records(body, lambda records: [])


def _append_unmatched_brace(body: bytes) -> bytes:
    return body + b"{"


def _append_trailing_comma(body: bytes) -> bytes:
    return body + b","


def _append_invalid_token(body: bytes) -> bytes:
    return body + b" INVALID"


def _prepend_unclosed_array(body: bytes) -> bytes:
    return b"[" + body


MALFORMED_JSON_HANDLERS: tuple[FaultHandler, ...] = (
    _append_unmatched_brace,
    _append_trailing_comma,
    _append_invalid_token,
    _prepend_unclosed_array,
)


@register_fault("malformed_json")
class MalformedJsonFault(ResponseBodyFault):
    def transform_body(self, body: bytes) -> bytes:
        return random.choice(MALFORMED_JSON_HANDLERS)(body)


@register_fault("truncated_response")
class TruncatedResponseFault(ResponseBodyFault):
    json_only = False
    update_content_length = False

    def transform_body(self, body: bytes) -> bytes:
        if not body:
            return body
        return body[: random.randint(0, len(body) - 1)]
