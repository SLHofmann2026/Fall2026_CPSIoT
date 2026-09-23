#!/usr/bin/env python3
"""Small classroom demos that invoke the installed Z3 command-line solver.

The script deliberately uses SMT-LIB and the z3 executable instead of the
Python z3 package. This keeps the demo transparent: students can inspect the
exact constraints sent to the solver.
"""

from __future__ import annotations

import argparse
import inspect
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass

from controller_logic import (
    feeder_next_breaker_closed,
    feeder_relay_trip,
    feeder_sensor,
    tank_inlet_open,
    tank_sensor,
    tank_unsafe,
)


def require_z3() -> str:
    path = shutil.which("z3")
    if not path:
        raise SystemExit("z3 was not found on PATH. Install Z3 or add its binary to PATH.")
    return path


def run_z3(smt: str) -> str:
    proc = subprocess.run(
        [require_z3(), "-in"],
        input=smt,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "z3 failed")
    return proc.stdout.strip()


def tokenize_sexpr(text: str) -> list[str]:
    return re.findall(r"\(|\)|[^\s()]+", text)


def parse_sexprs(text: str) -> list[object]:
    tokens = tokenize_sexpr(text)
    pos = 0

    def parse_one() -> object:
        nonlocal pos
        if pos >= len(tokens):
            raise ValueError("unexpected end of S-expression")
        token = tokens[pos]
        pos += 1
        if token != "(":
            return token
        result: list[object] = []
        while pos < len(tokens) and tokens[pos] != ")":
            result.append(parse_one())
        if pos >= len(tokens):
            raise ValueError("unclosed S-expression")
        pos += 1
        return result

    result = []
    while pos < len(tokens):
        result.append(parse_one())
    return result


def scalar(value: object) -> int | bool | str:
    if isinstance(value, str):
        if value == "true":
            return True
        if value == "false":
            return False
        try:
            return int(value)
        except ValueError:
            return value
    if isinstance(value, list) and len(value) == 2 and value[0] == "-":
        return -int(str(value[1]))
    return str(value)


def values_from_output(output: str) -> tuple[str, dict[str, int | bool | str]]:
    lines = output.splitlines()
    if not lines:
        raise ValueError("z3 produced no output")
    status = lines[0].strip()
    values: dict[str, int | bool | str] = {}
    if status == "sat" and len(lines) > 1:
        exprs = parse_sexprs("\n".join(lines[1:]))
        if exprs and isinstance(exprs[0], list):
            for pair in exprs[0]:
                if isinstance(pair, list) and len(pair) == 2:
                    values[str(pair[0])] = scalar(pair[1])
    return status, values


def print_smt(smt: str) -> None:
    print("\nExact SMT-LIB sent to Z3")
    print("-" * 72)
    print(smt.rstrip())
    print("-" * 72)


def print_functions(title: str, functions: list[object], mappings: list[str]) -> None:
    print(f"\n{title}")
    print("-" * 72)
    for function in functions:
        print(inspect.getsource(function).rstrip())
        print()
    print("The teaching front end mirrors those expressions as SMT assertions:")
    for mapping in mappings:
        print(f"  {mapping}")
    print("Z3 receives the assertions, not the Python source file.")
    print("-" * 72)


def tank_smt(no_spoof: bool, include_values: bool) -> str:
    lines = [
        "(set-option :produce-models true)",
        "(set-option :produce-unsat-cores true)",
        "(set-logic QF_LIA)",
        "(declare-const h_true Int)",
        "(declare-const bias Int)",
        "(declare-const h_reported Int)",
        "(assert (! (and (<= 0 h_true) (<= h_true 100)) :named physical_range))",
        "(assert (! (= h_reported (+ h_true bias)) :named sensor_model))",
        "(assert (! (>= h_true 90) :named property_violation))",
        "(assert (! (< h_reported 80) :named controller_open_path))",
        "(assert (! (and (<= -30 bias) (<= bias 0)) :named analysis_bound))",
    ]
    if no_spoof:
        lines.append("(assert (! (= bias 0) :named no_spoofing))")
    lines.append("(check-sat)")
    if include_values:
        lines.append("(get-value (h_true bias h_reported))")
    elif no_spoof:
        lines.append("(get-unsat-core)")
    return "\n".join(lines) + "\n"


def tank_demo(no_spoof: bool, show_smt: bool, show_code: bool) -> None:
    print("\nTANK SENSOR-BIAS QUERY")
    print("=" * 72)
    print("Find values satisfying all four conditions:")
    print("  property violation   h_true >= 90")
    print("  sensor model         h_reported = h_true + bias")
    print("  controller path      h_reported < 80")
    print("  analysis bound       -30 <= bias <= 0")
    if no_spoof:
        print("  added assumption     bias = 0")

    if show_code:
        print_functions(
            "EXECUTABLE TANK CODE AND ITS SMT MAPPING",
            [tank_sensor, tank_inlet_open, tank_unsafe],
            [
                "return h_true + bias    -> (= h_reported (+ h_true bias))",
                "return h_reported < 80  -> (< h_reported 80)",
                "return h_true >= 90     -> (>= h_true 90)",
                "analyst-supplied bound  -> (and (<= -30 bias) (<= bias 0))",
            ],
        )

    base = tank_smt(no_spoof=no_spoof, include_values=False)
    if show_smt:
        print_smt(base)
    status = run_z3(base).splitlines()[0].strip()
    print(f"\nZ3 result: {status.upper()}")
    if status == "sat":
        output = run_z3(tank_smt(no_spoof=no_spoof, include_values=True))
        _, values = values_from_output(output)
        true = int(values["h_true"])
        bias = int(values["bias"])
        reported = int(values["h_reported"])
        if tank_sensor(true, bias) != reported:
            raise AssertionError("SMT sensor relation disagrees with executable tank_sensor")
        if not tank_inlet_open(reported):
            raise AssertionError("SMT controller path disagrees with executable tank_inlet_open")
        if not tank_unsafe(true):
            raise AssertionError("SMT violation disagrees with executable tank_unsafe")
        print("One solver-generated witness:")
        print(f"  h_true     = {true}%")
        print(f"  bias       = {bias}%")
        print(f"  h_reported = {reported}%")
        print(f"  checks     = {true} >= 90, {reported} < 80, {true} + ({bias}) = {reported}")
        print("The exact witness may differ from the slide. Any satisfying assignment is valid.")
    elif status == "unsat":
        output = run_z3(tank_smt(no_spoof=no_spoof, include_values=False))
        lines = output.splitlines()
        if len(lines) > 1:
            print(f"Unsat core: {lines[1]}")
        print("With an accurate sensor, an unsafe true level cannot also satisfy the open-path condition.")
    else:
        print("Z3 returned unknown.")


@dataclass(frozen=True)
class GridConfig:
    feeders: int = 4
    steps: int = 6
    no_spoof: bool = False


def grid_names(cfg: GridConfig) -> list[str]:
    names = ["bad_f", "bad_t"]
    for f in range(cfg.feeders):
        for t in range(cfg.steps):
            names.extend(
                [
                    f"true_{f}_{t}",
                    f"bias_{f}_{t}",
                    f"reported_{f}_{t}",
                    f"trip_{f}_{t}",
                    f"closed_{f}_{t}",
                ]
            )
    return names


def grid_smt(cfg: GridConfig, include_values: bool) -> str:
    n, steps = cfg.feeders, cfg.steps
    if n < 1 or steps < 4:
        raise ValueError("grid demo needs at least 1 feeder and 4 steps")

    lines = [
        "(set-option :produce-models true)",
        "(set-logic QF_LIA)",
        "(declare-const bad_f Int)",
        "(declare-const bad_t Int)",
    ]
    for f in range(n):
        for t in range(steps):
            lines.extend(
                [
                    f"(declare-const true_{f}_{t} Int)",
                    f"(declare-const bias_{f}_{t} Int)",
                    f"(declare-const reported_{f}_{t} Int)",
                    f"(declare-const trip_{f}_{t} Bool)",
                    f"(declare-const closed_{f}_{t} Bool)",
                ]
            )

    for f in range(n):
        for t in range(steps):
            lines.extend(
                [
                    f"(assert (and (<= 70 true_{f}_{t}) (<= true_{f}_{t} 140)))",
                    f"(assert (and (<= -40 bias_{f}_{t}) (<= bias_{f}_{t} 0)))",
                    f"(assert (= reported_{f}_{t} (+ true_{f}_{t} bias_{f}_{t})))",
                    f"(assert (= trip_{f}_{t} (>= reported_{f}_{t} 100)))",
                ]
            )
            if cfg.no_spoof:
                lines.append(f"(assert (= bias_{f}_{t} 0))")
            if t == 0:
                lines.extend(
                    [
                        f"(assert (= true_{f}_{t} 90))",
                        f"(assert closed_{f}_{t})",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"(assert (<= -5 (- true_{f}_{t} true_{f}_{t-1})))",
                        f"(assert (<= (- true_{f}_{t} true_{f}_{t-1}) 10))",
                        f"(assert (= closed_{f}_{t} (and closed_{f}_{t-1} (not trip_{f}_{t-1}))))",
                    ]
                )

    for t in range(steps):
        current_sum = " ".join(f"true_{f}_{t}" for f in range(n))
        lines.append(f"(assert (= (+ {current_sum}) {n * 90 + 5 * t}))")
        attack_terms = " ".join(f"(ite (< bias_{f}_{t} 0) 1 0)" for f in range(n))
        lines.append(f"(assert (<= (+ {attack_terms}) 1))")

    bad_cases = []
    for f in range(n):
        for t in range(1, steps):
            bad_cases.append(
                f"(and (= bad_f {f}) (= bad_t {t}) closed_{f}_{t} "
                f"(>= true_{f}_{t} 120) (not trip_{f}_{t}))"
            )
    lines.extend(
        [
            f"(assert (and (<= 0 bad_f) (< bad_f {n})))",
            f"(assert (and (<= 1 bad_t) (< bad_t {steps})))",
            f"(assert (or {' '.join(bad_cases)}))",
            "(check-sat)",
        ]
    )
    if include_values:
        lines.append(f"(get-value ({' '.join(grid_names(cfg))}))")
    return "\n".join(lines) + "\n"


def naive_grid_space(cfg: GridConfig) -> tuple[int, float]:
    choices_per_feeder_step = 71 * 41 * 2
    exponent = cfg.feeders * cfg.steps
    log10 = exponent * math.log10(choices_per_feeder_step)
    return choices_per_feeder_step, log10


def grid_demo(cfg: GridConfig, show_smt: bool, show_code: bool) -> None:
    print("\nDISTRIBUTION-FEEDER PROTECTION QUERY")
    print("=" * 72)
    print(f"Model: {cfg.feeders} feeders over {cfg.steps} discrete steps")
    print("Controller: trip when reported current >= 100 A; breaker opens on the next step")
    print("Plant bound: each feeder changes by -5 A to +10 A per step")
    print("Shared demand: total feeder current rises by 5 A per step")
    print("Attack model: at most one feeder receives a negative sensor bias per step")
    print("Violation: true current >= 120 A while the breaker remains closed and no trip is issued")
    if cfg.no_spoof:
        print("Added assumption: every sensor bias equals 0")

    if show_code:
        print_functions(
            "EXECUTABLE FEEDER CODE AND ITS SMT MAPPING",
            [feeder_sensor, feeder_relay_trip, feeder_next_breaker_closed],
            [
                "sensor at f,t     -> (= reported_f_t (+ true_f_t bias_f_t))",
                "relay at f,t      -> (= trip_f_t (>= reported_f_t 100))",
                "breaker t to t+1  -> (= closed_f_t+1 (and closed_f_t (not trip_f_t)))",
                "environment model -> bounded current changes and shared total demand",
                "attack model      -> at most one negative bias at each step",
            ],
        )

    choices, log10 = naive_grid_space(cfg)
    print("\nNaive assignment space before transition constraints:")
    print(
        f"  ({choices:,} choices per feeder-step)^({cfg.feeders} feeders x {cfg.steps} steps)"
    )
    print(f"  approximately 10^{log10:.1f} assignments")

    base = grid_smt(cfg, include_values=False)
    if show_smt:
        print_smt(base)
    status = run_z3(base).splitlines()[0].strip()
    print(f"\nZ3 result: {status.upper()}")
    if status != "sat":
        if status == "unsat" and cfg.no_spoof:
            print("No bounded counterexample exists under the accurate-sensor assumption.")
        return

    output = run_z3(grid_smt(cfg, include_values=True))
    _, values = values_from_output(output)
    bad_f = int(values["bad_f"])
    bad_t = int(values["bad_t"])
    print(f"Counterexample: feeder {bad_f}, step {bad_t}")
    print("\n step | true A | bias A | reported A | trip | breaker closed")
    print("------+--------+--------+------------+------+---------------")
    for t in range(cfg.steps):
        true = int(values[f"true_{bad_f}_{t}"])
        bias = int(values[f"bias_{bad_f}_{t}"])
        reported = int(values[f"reported_{bad_f}_{t}"])
        trip = bool(values[f"trip_{bad_f}_{t}"])
        closed = bool(values[f"closed_{bad_f}_{t}"])
        marker = "  <-- violation" if t == bad_t else ""
        if feeder_sensor(true, bias) != reported:
            raise AssertionError("SMT sensor relation disagrees with executable feeder_sensor")
        if feeder_relay_trip(reported) != trip:
            raise AssertionError("SMT relay condition disagrees with executable feeder_relay_trip")
        if t > 0:
            previous_closed = bool(values[f"closed_{bad_f}_{t-1}"])
            previous_trip = bool(values[f"trip_{bad_f}_{t-1}"])
            if feeder_next_breaker_closed(previous_closed, previous_trip) != closed:
                raise AssertionError("SMT transition disagrees with executable breaker update")
        print(
            f" {t:>4} | {true:>6} | {bias:>6} | {reported:>10} | "
            f"{str(trip):>4} | {str(closed):>13}{marker}"
        )
    print("\nThe solver reasons over the whole bounded trace without enumerating every raw assignment.")


def scaling_demo(feeders: int, steps: int) -> None:
    cfg = GridConfig(feeders=feeders, steps=steps)
    choices, log10 = naive_grid_space(cfg)
    print("\nSTATE-SPACE GROWTH")
    print("=" * 72)
    print("This is a deliberately loose upper bound before applying transition constraints.")
    print(f"Current choices: 71; bias choices: 41; breaker states: 2")
    print(f"Choices per feeder-step: {choices:,}")
    print("\n feeders | steps | feeder-steps | approximate raw assignments")
    print("---------+-------+--------------+----------------------------")
    examples = [(1, 4), (2, 4), (4, 6), (8, 10), (feeders, steps)]
    seen = set()
    for f, t in examples:
        if (f, t) in seen:
            continue
        seen.add((f, t))
        _, scale = naive_grid_space(GridConfig(feeders=f, steps=t))
        print(f" {f:>7} | {t:>5} | {f*t:>12} | 10^{scale:>7.1f}")
    print("\nMore devices, state variables, or time steps multiply the search space.")
    print("Constraints, abstraction, compositional reasoning, and solver heuristics determine what remains tractable.")


def pause_if_requested(enabled: bool) -> None:
    if enabled and sys.stdin.isatty():
        input("\nPress Enter for the next query...")


def all_demo(pause: bool) -> None:
    tank_demo(no_spoof=False, show_smt=False, show_code=False)
    pause_if_requested(pause)
    tank_demo(no_spoof=True, show_smt=False, show_code=False)
    pause_if_requested(pause)
    grid_demo(GridConfig(), show_smt=False, show_code=False)
    pause_if_requested(pause)
    grid_demo(GridConfig(no_spoof=True), show_smt=False, show_code=False)
    pause_if_requested(pause)
    scaling_demo(feeders=8, steps=10)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    tank = sub.add_parser("tank", help="solve the tank sensor-bias query")
    tank.add_argument("--no-spoof", action="store_true", help="add bias = 0")
    tank.add_argument("--show-code", action="store_true", help="print executable code and its SMT mapping")
    tank.add_argument("--show-smt", action="store_true", help="print the exact SMT-LIB")

    grid = sub.add_parser("grid", help="solve the bounded feeder-protection query")
    grid.add_argument("--feeders", type=int, default=4)
    grid.add_argument("--steps", type=int, default=6)
    grid.add_argument("--no-spoof", action="store_true", help="set every bias to zero")
    grid.add_argument("--show-code", action="store_true", help="print executable code and its SMT mapping")
    grid.add_argument("--show-smt", action="store_true", help="print the exact SMT-LIB")

    scale = sub.add_parser("scale", help="show raw state-space growth")
    scale.add_argument("--feeders", type=int, default=8)
    scale.add_argument("--steps", type=int, default=10)

    all_cmd = sub.add_parser("all", help="run the full classroom sequence")
    all_cmd.add_argument("--pause", action="store_true", help="pause between sections")
    return p


def main() -> None:
    args = parser().parse_args()
    if args.command == "tank":
        tank_demo(no_spoof=args.no_spoof, show_smt=args.show_smt, show_code=args.show_code)
    elif args.command == "grid":
        grid_demo(
            GridConfig(feeders=args.feeders, steps=args.steps, no_spoof=args.no_spoof),
            show_smt=args.show_smt,
            show_code=args.show_code,
        )
    elif args.command == "scale":
        scaling_demo(feeders=args.feeders, steps=args.steps)
    else:
        all_demo(pause=args.pause)


if __name__ == "__main__":
    main()
