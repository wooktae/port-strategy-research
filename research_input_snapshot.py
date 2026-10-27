"""Generates a deterministic Snapshot Hash of the input data actually consumed by the Research Backtest."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


class InputSnapshotError(ValueError):
    """Raised when the input Snapshot composition or finalized state is invalid."""


SPECIAL_VALUE_KEY = "__research_special_value__"
SPECIAL_NAN = "NaN"
SPECIAL_POSITIVE_INFINITY = "Infinity"
SPECIAL_NEGATIVE_INFINITY = "-Infinity"
SPECIAL_PANDAS_NA = "PANDAS_NA"


def _special_value(label: str) -> dict[str, str]:
    return {SPECIAL_VALUE_KEY: label}


def _canonicalize(value: Any) -> Any:
    # Keep None as an actual JSON null.
    if value is None:
        return None

    # pandas.NA cannot be evaluated as a bool at all, so identify it first.
    if value is pd.NA:
        return _special_value(SPECIAL_PANDAS_NA)

    # Reduce a numpy scalar to a Python scalar, then apply the same rules.
    if isinstance(value, np.generic):
        return _canonicalize(value.item())

    if isinstance(value, Decimal):
        if value.is_nan():
            return _special_value(SPECIAL_NAN)
        if value.is_infinite():
            return _special_value(
                SPECIAL_POSITIVE_INFINITY
                if value > 0
                else SPECIAL_NEGATIVE_INFINITY
            )
        return str(value)

    if isinstance(value, float):
        if math.isnan(value):
            return _special_value(SPECIAL_NAN)
        if math.isinf(value):
            return _special_value(
                SPECIAL_POSITIVE_INFINITY
                if value > 0
                else SPECIAL_NEGATIVE_INFINITY
            )
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_canonicalize(item) for item in value]

    if isinstance(value, (str, int, bool)):
        return value

    if hasattr(value, "to_dict"):
        return _canonicalize(value.to_dict())

    raise InputSnapshotError(
        "INPUT_SNAPSHOT_UNSUPPORTED_TYPE="
        f"{type(value).__name__}"
    )


def _canonical_json(value: Any) -> str:
    return json.dumps(
        _canonicalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _count_special_values(value: Any) -> dict[str, int]:
    counts = {
        SPECIAL_NAN: 0,
        SPECIAL_POSITIVE_INFINITY: 0,
        SPECIAL_NEGATIVE_INFINITY: 0,
        SPECIAL_PANDAS_NA: 0,
    }

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            if set(item) == {SPECIAL_VALUE_KEY}:
                label = item[SPECIAL_VALUE_KEY]
                if label in counts:
                    counts[label] += 1
                return
            for nested in item.values():
                walk(nested)
            return

        if isinstance(item, Sequence) and not isinstance(
            item,
            (str, bytes, bytearray),
        ):
            for nested in item:
                walk(nested)

    walk(value)
    return counts


@dataclass(frozen=True)
class InputSnapshotEvidence:
    """Finalized input Snapshot Hash and the minimal Manifest."""

    snapshot_hash: str
    manifest_json: str
    dataset_count: int
    item_count: int
    special_value_count: int
    status: str = "COMPLETE"


class InputSnapshotBuilder:
    """Builds a deterministic Hash keyed by Dataset Key, independent of the actual consumption order."""

    def __init__(self) -> None:
        self._datasets: dict[str, dict[str, Any]] = {}
        self._finalized = False

    def add(
        self,
        dataset_name: str,
        dataset_key: str,
        value: Any,
    ) -> None:
        if self._finalized:
            raise InputSnapshotError(
                "INPUT_SNAPSHOT_ALREADY_FINALIZED"
            )

        normalized_name = dataset_name.strip()
        normalized_key = dataset_key.strip()

        if not normalized_name:
            raise InputSnapshotError(
                "INPUT_SNAPSHOT_DATASET_NAME_REQUIRED"
            )
        if not normalized_key:
            raise InputSnapshotError(
                "INPUT_SNAPSHOT_DATASET_KEY_REQUIRED"
            )

        dataset = self._datasets.setdefault(
            normalized_name,
            {},
        )

        if normalized_key in dataset:
            raise InputSnapshotError(
                "INPUT_SNAPSHOT_DUPLICATE_ITEM="
                f"{normalized_name}:{normalized_key}"
            )

        dataset[normalized_key] = _canonicalize(value)

    def finalize(self) -> InputSnapshotEvidence:
        if self._finalized:
            raise InputSnapshotError(
                "INPUT_SNAPSHOT_ALREADY_FINALIZED"
            )

        if not self._datasets:
            raise InputSnapshotError(
                "INPUT_SNAPSHOT_EMPTY"
            )

        self._finalized = True

        canonical_payload = {
            dataset_name: {
                dataset_key: dataset_items[dataset_key]
                for dataset_key in sorted(dataset_items)
            }
            for dataset_name, dataset_items in sorted(
                self._datasets.items()
            )
        }
        canonical_json = _canonical_json(canonical_payload)
        snapshot_hash = hashlib.sha256(
            canonical_json.encode("utf-8")
        ).hexdigest()

        special_counts = _count_special_values(canonical_payload)
        special_value_count = sum(special_counts.values())

        manifest = {
            "datasets": {
                dataset_name: {
                    "item_count": len(dataset_items),
                    "keys": sorted(dataset_items),
                }
                for dataset_name, dataset_items in sorted(
                    self._datasets.items()
                )
            },
            "dataset_count": len(self._datasets),
            "item_count": sum(
                len(dataset_items)
                for dataset_items in self._datasets.values()
            ),
            "missing_data_contract": {
                "missing_price_row": (
                    "preserved_as_absent_row_without_imputation"
                ),
                "null": "preserved_as_json_null",
                "special_numeric_values": (
                    "preserved_as_explicit_special_value_marker"
                ),
                "imputation": "disabled",
            },
            "special_value_counts": special_counts,
            "special_value_count": special_value_count,
        }

        return InputSnapshotEvidence(
            snapshot_hash=snapshot_hash,
            manifest_json=_canonical_json(manifest),
            dataset_count=manifest["dataset_count"],
            item_count=manifest["item_count"],
            special_value_count=special_value_count,
        )
