#!/usr/bin/env python3
"""Transparent bounded search over network-observation attack parameters."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import pathlib
import sys
from typing import Iterable

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from controller_semantics import ControllerState, step_controller  # noqa: E402


def load_tank_model():
    path = HERE.parent / "cps_tank.py"
    spec = importlib.util.spec_from_file_location("hw2_search_tank", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def evaluate(initial: float, spoof_after: float, sensor_bias: float, duration: int = 36) -> dict:
    model = load_tank_model()
    tank = model.Tank(level=initial)
    controller = ControllerState()
    maximum = tank.level
    first_violation = None
    for elapsed in range(duration + 1):
        honest = tank.sensor_reading()
        delivered = honest if elapsed < spoof_after else max(5.0, tank.sensor_reading(sensor_bias))
        valve_open = step_controller(delivered, controller)
        maximum = max(maximum, tank.level)
        if first_violation is None and tank.level >= model.HIGH_HIGH_LEVEL:
            first_violation = float(elapsed)
        tank.advance("OPEN" if valve_open else "CLOSED", 1.0)
    return {
        "initial_level_pct": initial,
        "spoof_after_s": spoof_after,
        "sensor_bias_pct": sensor_bias,
        "maximum_true_level_pct": maximum,
        "first_violation_s": "" if first_violation is None else first_violation,
        "physical_property": "PASS" if first_violation is None else "FAIL",
    }


def search(initials: Iterable[float], starts: Iterable[float], biases: Iterable[float]) -> list[dict]:
    return [evaluate(initial, start, bias) for initial in initials for start in starts for bias in biases]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "For a one-dimensional Part D search, provide one fixed value for "
            "each dimension you are not varying. Result columns such as "
            "first_violation_s and physical_property are outcomes, not inputs."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--initial",
        type=float,
        nargs="+",
        default=[40.0, 50.0, 60.0],
        help="initial true tank level(s), in percent",
    )
    parser.add_argument(
        "--start",
        type=float,
        nargs="+",
        default=[4.0, 8.0, 12.0],
        help="time(s) when sensor bias begins; emitted as spoof_after_s",
    )
    parser.add_argument(
        "--bias",
        type=float,
        nargs="+",
        default=[-20.0, -35.0, -50.0],
        help="sensor bias value(s), in percentage points",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=HERE / "runs" / "search-results.csv",
        help="destination CSV containing tested inputs and oracle outcomes",
    )
    args = parser.parse_args()
    rows = search(args.initial, args.start, args.bias)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    failures = sum(row["physical_property"] == "FAIL" for row in rows)
    print(f"{len(rows)} bounded tests; {failures} counterexamples; {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
