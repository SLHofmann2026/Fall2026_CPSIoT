# Live agent authority demo

This classroom demo lets a local language model summarize alarm evidence and optionally propose a control action. Python permission rules decide whether that proposal executes. The only effect target is `SimulatedPlant`, an in-memory representation of a trip threshold. It is neither a spoofed plant nor a connected physical device.

```text
task + supplied example read-tool results
        |
        v
local model summary + optional control proposal (variable)
        |
        v
deterministic policy gate
        |
        +-- DENY -> no effect
        |
        +-- ALLOW -> simulated threshold state only
        |
        v
JSONL audit evidence
```

The model may comply, refuse, or behave oddly. That variability is part of the lesson. It can only select a fixed candidate action, not invent tool arguments. In this code path, the executor updates state only after an `ALLOW` decision.

## What students are predicting

The two observations are **inputs**, not action choices. After reading both, the model chooses between:

1. **Summary / escalation only:** return `candidate_id: null`, request no control change, and still provide a useful summary.
2. **Propose a threshold change:** select `set-p1-hh-trip-150`. The application maps that ID to the fixed `set_trip_threshold(P1_HH_TRIP, 150)` request.

The script displays this menu before asking students to predict the model's choice. Students predict a request; they are not choosing which read tool should run. Selecting a control action does not authorize it. Under the default policy, an alarm-triage task cannot change the threshold.

`clean` means the baseline inputs contain no injected instruction. It does not promise correct model behavior: even this case may produce a threshold-change proposal. Show the actual result rather than forcing a refusal. The Python gate still blocks the write.

## Where observations come from

The script loads an alarm log and maintenance note from `fixtures/scenarios.json`. They represent already-returned read-tool results. **No separate observation agent runs**, and the model does not call or select these read tools during this exercise.

The exercise assumes the sample alarm log is reliable. It treats the maintenance note as external text that may contain misleading instructions; the poisoned case deliberately supplies such a note. These are explicit teaching assumptions, not a claim that real-world sensors, retrieval systems, or other agents work perfectly. The experiment isolates the model's proposal and the application's authorization decision. It does not test live retrieval, sensor accuracy, or a multi-agent observation pipeline.

## Why JSON appears

JSON gives Python named fields it can parse. The model returns a `summary` and a `candidate_id`. The application validates the ID and supplies fixed tool arguments. JSON formatting itself grants no permission.

The terminal uses plain-language explanations by default. Add `--details` to inspect JSON observations, model replies, normalized requests, policy decisions, and effects. JSONL audit files remain machine-readable in either mode.

The policy gate is ordinary deterministic Python, not another LLM. It reads application-held task, role, approval and process-state fixtures. In a production design, these need authenticated identities and trusted state, with authorization on every effect path. The demo's gate and executor share one Python process; this is not an isolated or tamper-resistant production enforcement boundary.

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

After the script reveals both observations and the two-choice action menu, ask students to predict **summary only or threshold-change proposal**. A no-action choice still produces a summary. After the model reply, pause on this question:

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
3. Same engineer/request in MAINTENANCE -> `ALLOW` against the simulated plant.
4. Deliberately bad role-only policy while RUNNING -> unsafe `ALLOW`.
5. Restore the state-aware policy and replay -> `DENY`.

This sequence does not call an LLM. Each case starts with fresh simulated state at 120. It shows that engineering authority can be necessary but insufficient: current process state can still prohibit an operation.

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
--details             also show the JSON behind the readable walkthrough
--policy role-only    use the deliberately weak policy for a case
```

Audit records are written to ignored `runs/*.jsonl` files. They contain task identity, supplied observations, available choices, normalized proposal, policy verdict and reason, and simulated effect before/after state. They do not record hidden reasoning. Effect records use `simulated_adapter: true`; older captures used `fake_adapter`. Existing logs are not rewritten.

## Claims this demo supports

- A model can be treated as an uncertain proposer rather than the enforcement boundary.
- Identical actions can have different causal and authorization histories.
- Capability and action policy can deny an effect independently of model output.
- CPS authorization can depend on actor, delegated task, approved change, target/range, and process state.
- Raw audit events let students distinguish proposal, decision, and effect.

## Claims this demo does not support

- The authored causal label proves which token caused a live model response.
- A local actor string is an authenticated production identity.
- The demonstration policy is deployed in a real controller or testbed.
- Application-level denial is a firewall, sandbox, credential revocation, or physical safety certification.
- One model run establishes a general prompt-injection success or failure rate.
