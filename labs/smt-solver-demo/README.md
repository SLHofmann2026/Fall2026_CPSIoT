# CPS SMT solver demo

This live demo sends actual SMT-LIB constraints to the installed Z3 solver. It has two examples:

1. The tank sensor-bias query from the lecture.
2. A bounded distribution-feeder protection model with multiple feeders and time steps.

No Python packages are required. The only external command is `z3`.

The executable controller fragments live in `controller_logic.py`. The demo prints those functions, shows the corresponding SMT assertions, asks Z3 to solve them, and checks the returned witness against the executable functions.

## Requirements

- Python 3.9 or newer.
- The Z3 command-line solver available as `z3` on `PATH`.

Check the environment before class:

```bash
python3 --version
z3 --version
```

On a personal macOS system, Z3 is available through Homebrew with `brew install z3`. On Ubuntu, the package is `z3`. In a course-managed environment, report a missing command to staff instead of installing software into the prepared image.

## Suggested classroom sequence

From this directory:

```bash
./run_demo.sh tank --show-code --show-smt
./run_demo.sh tank --no-spoof
./run_demo.sh grid --feeders 4 --steps 6 --show-code --show-smt
./run_demo.sh grid --feeders 4 --steps 6 --no-spoof
./run_demo.sh scale --feeders 8 --steps 10
```

Or run the complete sequence with pauses:

```bash
./run_demo.sh
```

## Teaching points

- `SAT` means the encoded constraints have at least one joint assignment. The model is a witness.
- `UNSAT` means no assignment satisfies every encoded constraint. It remains scoped to this model and bound.
- The tank solver may return a witness different from the one printed on the slide. Both can be valid.
- The feeder example introduces a bounded trace, controller state, breaker state, a shared demand constraint, and an attacker who can bias at most one feeder per step.
- The state-space calculation is a loose count of raw assignments before transition constraints. It illustrates growth, not the number of reachable states Z3 literally enumerates.

## How this maps to actual code

The comparisons and assignments in `controller_logic.py` are executable Python. The SMT model mirrors those expressions:

```text
return h_reported < 80
        |
        +---> (assert (< h_reported 80))
```

This teaching demo performs that translation explicitly so students can inspect it. Z3 does not read Python, C, Structured Text, or relay firmware directly. A production program-analysis tool first parses the source into an intermediate representation, follows program paths or unrolls transitions, and emits solver constraints. Symbolic execution tools automate that middle step.

The feeder environment constraints are model assumptions rather than relay source code. They bound load changes, couple feeder demand, and limit the attacker. A SAT result therefore establishes feasibility within that combined program-and-environment model.

## Feeder model

At every step, each feeder has a true current, sensor bias, reported current, trip command, and breaker state.

The relay issues a trip when reported current reaches 100 A. A violation requires true current to reach at least 120 A while the breaker remains closed and the relay does not trip. With bounded negative sensor bias, Z3 finds a counterexample. With all sensor biases fixed to zero, the bounded query becomes unsatisfiable.
