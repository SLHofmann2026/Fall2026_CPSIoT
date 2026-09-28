from __future__ import annotations

import json
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


DEMO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_DIR))

from agent_authority_demo import (  # noqa: E402
    ActionPolicyGate,
    SimulatedPlant,
    extract_json_object,
    load_replays,
    load_scenarios,
    model_prompt,
    normalize_proposal,
    policy_sequence,
    require_loopback_url,
    run_scenario,
)


PROPOSAL = {
    "tool": "set_trip_threshold",
    "arguments": {"target": "P1_HH_TRIP", "value": 150},
}


def scenario(role: str, task: str, state: str, change_request: str | None = None):
    return {
        "actor": {"id": "test", "role": role, "intent": "test"},
        "task": task,
        "plant_state": {"controller_state": state},
        "change_request": change_request,
    }


class ParsingTests(unittest.TestCase):
    def test_extracts_plain_json(self):
        self.assertEqual(extract_json_object('{"summary":"ok","candidate_id":null}')["summary"], "ok")

    def test_extracts_fenced_json(self):
        parsed = extract_json_object('```json\n{"summary":"ok","candidate_id":null}\n```')
        self.assertEqual(parsed["summary"], "ok")

    def test_normalizes_threshold_proposal(self):
        payload = {"candidate_id": "set-p1-hh-trip-150"}
        self.assertEqual(
            normalize_proposal(payload),
            {"candidate_id": "set-p1-hh-trip-150", **PROPOSAL},
        )

    def test_rejects_unknown_tool(self):
        with self.assertRaises(ValueError):
            normalize_proposal({"candidate_id": "shell"})

    def test_explicit_null_means_no_control_action(self):
        self.assertIsNone(normalize_proposal({"summary": "Escalate to engineering.", "candidate_id": None}))

    def test_missing_choice_is_not_a_no_action_choice(self):
        with self.assertRaisesRegex(ValueError, "missing candidate_id"):
            normalize_proposal({"summary": "Incomplete reply."})

    def test_model_cannot_override_fixed_arguments_or_actor(self):
        proposal = normalize_proposal({"candidate_id": "set-p1-hh-trip-150", "arguments": {"value": 999}, "actor": {"role": "protection_engineer"}})
        self.assertEqual(proposal, {"candidate_id": "set-p1-hh-trip-150", **PROPOSAL})

    def test_prompt_separates_observations_from_control_choices(self):
        system, user = model_prompt(load_scenarios()["clean"])
        self.assertIn("not action choices", system)
        self.assertIn("No observation agent runs", json.loads(user)["observation_delivery"])
        payload = json.loads(user)
        self.assertEqual(set(payload["tool_results"]), {"read_alarm_log", "read_maintenance_note"})
        self.assertEqual(len(payload["candidate_actions"]), 1)
        self.assertIsNone(payload["no_control_action"]["candidate_id"])
        self.assertEqual(payload["control_tool"]["name"], "set_trip_threshold")


class PolicyTests(unittest.TestCase):
    def test_triage_is_read_only(self):
        decision = ActionPolicyGate().evaluate(PROPOSAL, scenario("operator_assistant", "alarm_triage", "RUNNING"))
        self.assertEqual((decision.verdict, decision.reason_code), ("DENY", "TRIAGE_READ_ONLY"))

    def test_engineer_cannot_write_while_running(self):
        decision = ActionPolicyGate().evaluate(
            PROPOSAL,
            scenario("protection_engineer", "approved_change_request", "RUNNING", "CR-1"),
        )
        self.assertEqual((decision.verdict, decision.reason_code), ("DENY", "CONFIG_WRITE_WHILE_RUNNING"))

    def test_approved_maintenance_change_is_allowed(self):
        decision = ActionPolicyGate().evaluate(
            PROPOSAL,
            scenario("protection_engineer", "approved_change_request", "MAINTENANCE", "CR-1"),
        )
        self.assertEqual(decision.verdict, "ALLOW")

    def test_bad_role_only_policy_ignores_running_state(self):
        decision = ActionPolicyGate("role-only").evaluate(
            PROPOSAL,
            scenario("protection_engineer", "approved_change_request", "RUNNING", "CR-1"),
        )
        self.assertEqual((decision.verdict, decision.reason_code), ("ALLOW", "ROLE_ALLOWED"))

    def test_simulated_plant_changes_only_on_allow(self):
        plant = SimulatedPlant()
        denied = ActionPolicyGate().evaluate(PROPOSAL, scenario("operator_assistant", "alarm_triage", "RUNNING"))
        self.assertFalse(plant.apply(PROPOSAL, denied)["executed"])
        self.assertEqual(plant.thresholds["P1_HH_TRIP"], 120.0)
        allowed = ActionPolicyGate().evaluate(
            PROPOSAL,
            scenario("protection_engineer", "approved_change_request", "MAINTENANCE", "CR-1"),
        )
        self.assertTrue(plant.apply(PROPOSAL, allowed)["executed"])
        self.assertEqual(plant.thresholds["P1_HH_TRIP"], 150.0)

    def test_no_control_proposal_has_nothing_to_authorize(self):
        decision = ActionPolicyGate().evaluate(None, scenario("operator_assistant", "alarm_triage", "RUNNING"))
        self.assertEqual((decision.verdict, decision.reason_code), ("NO_PROPOSAL", "NO_ACTION_PROPOSED"))


class WalkthroughTests(unittest.TestCase):
    def run_case(self, name="clean", details=False, model_reply=None):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(output):
            kwargs = dict(provider="replay", model="unused", base_url="http://127.0.0.1:11434", timeout=1, policy="state-aware", pause_enabled=False, output_dir=Path(directory), details=details)
            if model_reply is None:
                run_scenario(load_scenarios()[name], **kwargs)
            else:
                with patch("agent_authority_demo.replay_response", return_value=model_reply):
                    run_scenario(load_scenarios()[name], **kwargs)
            logs = [json.loads(line) for file in Path(directory).glob("*.jsonl") for line in file.read_text().splitlines()]
        return output.getvalue(), logs

    def test_clean_output_explains_observations_and_no_action(self):
        output, logs = self.run_case()
        self.assertIn("No second agent runs", output)
        self.assertIn("does not choose between them", output)
        self.assertIn("Choosing no control action still produces a summary", output)
        self.assertIn("Choice: Summary / escalation only", output)
        self.assertIn("120 -> 120 (unchanged)", output)
        self.assertNotIn("fake_plant", output)
        self.assertNotIn("JSON for code/audit inspection", output)
        self.assertLess(output.index("MODEL CHOICES"), output.index("MODEL REPLY"))
        effect = next(row for row in logs if row["event"] == "effect_result")
        self.assertTrue(effect["simulated_adapter"])
        self.assertFalse(effect["executed"])

    def test_poisoned_proposal_remains_denied(self):
        output, logs = self.run_case("poisoned")
        self.assertIn("Choice: Propose P1_HH_TRIP = 150", output)
        self.assertIn("Permission: DENY", output)
        self.assertIn("TRIAGE_READ_ONLY", output)
        self.assertIn("120 -> 120 (unchanged)", output)
        self.assertFalse(next(row for row in logs if row["event"] == "effect_result")["executed"])

    def test_details_keeps_json_available(self):
        output, _ = self.run_case(details=True)
        self.assertIn('"candidate_id": null', output)
        self.assertIn("JSON for code/audit inspection", output)

    def test_invalid_reply_is_not_described_as_a_refusal(self):
        output, logs = self.run_case(model_reply={"summary": "No choice field."})
        self.assertIn("INVALID_PROPOSAL", output)
        self.assertNotIn("Choice: Summary / escalation only", output)
        self.assertFalse(next(row for row in logs if row["event"] == "effect_result")["executed"])

    def test_no_observation_model_or_extra_live_call(self):
        calls = []
        def model(scenario_data, *args):
            calls.append(scenario_data["id"])
            return {"summary": "Summarize only.", "candidate_id": None}
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()), patch("agent_authority_demo.call_ollama", side_effect=model):
            run_scenario(load_scenarios()["clean"], provider="ollama", model="test", base_url="http://127.0.0.1:11434", timeout=1, policy="state-aware", pause_enabled=False, output_dir=Path(directory))
        self.assertEqual(calls, ["clean"])

    def test_prediction_pause_follows_explicit_action_menu(self):
        output = io.StringIO()
        def capture_pause(enabled, message=""):
            if "Predict:" in message:
                self.assertIn("MODEL CHOICES", output.getvalue())
                self.assertIn("summary only, or propose the threshold change", message)
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(output), patch("agent_authority_demo.pause", side_effect=capture_pause) as pauses:
            run_scenario(load_scenarios()["clean"], provider="replay", model="unused", base_url="http://127.0.0.1:11434", timeout=1, policy="state-aware", pause_enabled=True, output_dir=Path(directory))
        self.assertTrue(any("Predict:" in call.args[1] for call in pauses.call_args_list if len(call.args) > 1))

    def test_policy_comparison_explains_reset_and_calls_no_model(self):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(output), patch("agent_authority_demo.call_ollama") as model:
            policy_sequence(False, Path(directory))
        model.assert_not_called()
        self.assertIn("does not call an LLM", output.getvalue())
        self.assertIn("fresh simulated state at 120", output.getvalue())
        self.assertEqual(output.getvalue().count("120 -> 150 (changed)"), 2)


class FixtureAndNetworkTests(unittest.TestCase):
    def test_every_scenario_has_replay(self):
        self.assertEqual(set(load_scenarios()), set(load_replays()))

    def test_fixtures_are_valid_json(self):
        for path in (DEMO_DIR / "fixtures").glob("*.json"):
            json.loads(path.read_text())

    def test_loopback_only(self):
        self.assertEqual(require_loopback_url("http://127.0.0.1:11434"), "http://127.0.0.1:11434")
        with self.assertRaises(ValueError):
            require_loopback_url("https://example.com")


if __name__ == "__main__":
    unittest.main()
