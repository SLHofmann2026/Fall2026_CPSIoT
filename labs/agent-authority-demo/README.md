# Live agent authority demo

This classroom demo lets a local language model propose a consequential-looking CPS action, then sends the proposal through an independent deterministic policy gate. The only effect target is an in-memory fake plant object.

```text
task + retrieved observations
        |
        v
local model proposal (variable)
        |
        v
deterministic policy gate
        |
        +-- DENY -> no effect
        |
        +-- ALLOW -> fake threshold state only
        |
        v
JSONL audit evidence
```

The model may comply, refuse, or behave oddly. That variability is part of the lesson. It can only select a fixed candidate action, not invent tool arguments. The security property is that even the bounded proposal cannot bypass the gate.

## Safety boundary

- No PLC, SPHERE, Rockwell, shell, filesystem-write, network-control, or credential tool exists.
- The Ollama endpoint must be on loopback. External model services are rejected.
- The only consequential candidate is the fixed `set_trip_threshold(P1_HH_TRIP, 150)` action.
- An allowed action changes only an in-memory dictionary that starts at `P1_HH_TRIP=120`.
- Saved proposals provide an explicit replay fallback; they are never presented as live output.
- Causal labels are authored fixture evidence. The demo does not infer prompt provenance or expose chain-of-thought.

## Requirements

- Python 3.9 or newer.
- Optional live mode: Ollama running locally with a model already installed.
- Replay mode: no model runtime or Python package is required.

The default live model is `llama3.1`. Select another installed model with `--model` or `DEMO_MODEL`. Do not download a model during class.

## Pre-class check

```bash
./run_demo.sh check
python3 -m unittest discover -s tests -v
./run_demo.sh run poisoned --provider ollama
./run_demo.sh run poisoned --provider replay
```

`check` exits successfully when Ollama is unavailable because replay mode remains usable. Use `--provider ollama` for a strict live test.

## Monday sequence: failure attribution

Run the complete sequence with pauses:

```bash
./run_demo.sh
```

For a tighter 7-9 minute sequence:

```bash
./run_demo.sh run clean --provider ollama --pause
./run_demo.sh run poisoned --provider ollama --pause
./run_demo.sh run malicious --provider ollama --pause
```

After each task and observation reveal, ask students to predict the proposal. After the proposal, pause on this question:

> The model has proposed something. What, independently, decides whether an effect occurs?

If the live model refuses the injected note, keep the result. Then show the captured proposal:

```bash
./run_demo.sh run poisoned --provider replay --pause
```

That supports the same conclusion: helpful model behavior is welcome, but the system does not rely on it.

The `overbroad` case varies the advertised capability instead of the retrieved text:

```bash
./run_demo.sh run overbroad --provider ollama --pause
```

All cases use the same deterministic `TRIAGE_READ_ONLY` denial if the model proposes the threshold change. The final attribution panel distinguishes observation integrity, capability/task scope, and principal authorization.

## Wednesday sequence: executable policy

```bash
./run_demo.sh policy-sequence --pause
```

The proposed action remains identical while the sequence changes actor, task, approved request, controller state, and policy version:

1. Triage assistant -> `DENY: TRIAGE_READ_ONLY`.
2. Protection engineer with an approved task while RUNNING -> `DENY: CONFIG_WRITE_WHILE_RUNNING`.
3. Same engineer/request in MAINTENANCE -> `ALLOW` against the fake plant.
4. Deliberately bad role-only policy while RUNNING -> unsafe `ALLOW`.
5. Restore the state-aware policy and replay -> `DENY`.

This shows that engineering authority can be necessary but insufficient: current process state can still prohibit an operation.

## Commands

```text
./run_demo.sh check
./run_demo.sh run clean|poisoned|overbroad|malicious|all [options]
./run_demo.sh policy-sequence [--pause]
```

Useful options:

```text
--provider auto       use local Ollama, visibly fall back to replay on connection/error
--provider ollama     require a live local model
--provider replay     use the saved proposal
--model NAME          select an installed Ollama model
--pause               pause between teaching reveals
--policy role-only    use the deliberately weak policy for a case
```

Audit records are written to ignored `runs/*.jsonl` files. They contain task identity, tool observations, normalized proposal, policy verdict and reason, and fake effect before/after state. They do not record hidden reasoning.

## Claims this demo supports

- A model can be treated as an uncertain proposer rather than the enforcement boundary.
- Identical actions can have different causal and authorization histories.
- Capability and action policy can deny an effect independently of model output.
- CPS authorization can depend on actor, delegated task, approved change, target/range, and process state.
- Raw audit events let students distinguish proposal, decision, and effect.

## Claims this demo does not support

- The authored causal label proves which token caused a live model response.
- A local actor string is an authenticated production identity.
- The fake policy is deployed in a real controller or testbed.
- Application-level denial is a firewall, sandbox, credential revocation, or physical safety certification.
- One model run establishes a general prompt-injection success or failure rate.
