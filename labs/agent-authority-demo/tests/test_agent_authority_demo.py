from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


DEMO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_DIR))

from agent_authority_demo import (  # noqa: E402
    ActionPolicyGate,
    FakePlant,
    extract_json_object,
    load_replays,
    load_scenarios,
    normalize_proposal,
    require_loopback_url,
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

    def test_fake_plant_changes_only_on_allow(self):
        plant = FakePlant()
        denied = ActionPolicyGate().evaluate(PROPOSAL, scenario("operator_assistant", "alarm_triage", "RUNNING"))
        self.assertFalse(plant.apply(PROPOSAL, denied)["executed"])
        self.assertEqual(plant.thresholds["P1_HH_TRIP"], 120.0)
        allowed = ActionPolicyGate().evaluate(
            PROPOSAL,
            scenario("protection_engineer", "approved_change_request", "MAINTENANCE", "CR-1"),
        )
        self.assertTrue(plant.apply(PROPOSAL, allowed)["executed"])
        self.assertEqual(plant.thresholds["P1_HH_TRIP"], 150.0)


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
