"""Bound the native audit externally; label stored-receipt checks separately.

Mihir Srivastava with substantial OpenAI Codex assistance; Apache-2.0.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import types

PACKAGE = Path(__file__).resolve().parent
module = types.ModuleType("owner_death_probe")
module.__file__ = str(PACKAGE / "probe.py")
exec(compile(Path(module.__file__).read_bytes(), module.__file__, "exec"), module.__dict__)
require = module.require


def check_receipt(receipt, hashes):
    require(receipt["schema"] == "windows-stream-owner-death/v1", "receipt schema")
    require(receipt["status"] == "PASS_WINDOWS_STREAM_OWNER_DEATH", "receipt status")
    require(receipt["source_sha256"] == hashes, "receipt source binding")
    require(receipt["probe_sha256"] == hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest(),
            "receipt probe binding")
    cases = receipt["cases"]
    require([x["case"] for x in cases] == list(module.CASES), "receipt case coverage/order")
    for item in cases:
        case = item["case"]
        require(item["observation_before_fixture_teardown"] is True
                and item["teardown_all_retained_processes_stopped"] is True, "observation/cleanup boundary")
        for name in ("gate_in_private_job", "target_started", "target_marker_after"):
            require(type(item[name]) is bool, "non-Boolean observation")
        expected_roles = {"owner", "gate"} | ({"target", "leaf"} if item["target_started"] else set())
        require(set(item["alive_after"]) == expected_roles, "process observation coverage")
        require(all(type(value) is bool for value in item["alive_after"].values()), "process liveness types")
        if case in ("early-release-control", "no-kill-control"):
            try:
                module.validate_observation(case, item)
            except module.AuditFailure as exc:
                require(item["counterfactual_rejected"] == str(exc), "counterfactual rejection changed")
            else:
                raise module.AuditFailure("counterfactual no longer rejects")
            require(all(item["alive_after"][name] for name in ("gate", "target", "leaf")),
                    "counterfactual did not expose surviving descendants")
        else:
            module.validate_observation(case, item)
    before_open, before_assign = cases[:2]
    require(before_open["gate_outcome"]["winerror"] == 2, "missing-event evidence")
    require(before_assign["gate_alive_after_owner_death"] is True
            and before_assign["gate_wait_result"] == 258
            and before_assign["gate_outcome"]["message"] == "replay ownership gate was not released",
            "pre-assignment timeout evidence")


def rejection_controls(receipt, hashes):
    mutations = []
    wrong_source = deepcopy(receipt)
    wrong_source["source_sha256"]["adapter"] = "0" * 64
    mutations.append(wrong_source)
    missing_case = deepcopy(receipt)
    missing_case["cases"].pop()
    mutations.append(missing_case)
    hidden_survivor = deepcopy(receipt)
    hidden_survivor["cases"][3]["alive_after"]["leaf"] = True
    mutations.append(hidden_survivor)
    cleanup_as_observation = deepcopy(receipt)
    cleanup_as_observation["cases"][3]["observation_before_fixture_teardown"] = False
    mutations.append(cleanup_as_observation)
    hidden_delay = deepcopy(receipt)
    hidden_delay["cases"][1]["gate_alive_after_owner_death"] = False
    mutations.append(hidden_delay)
    for mutant in mutations:
        try:
            check_receipt(mutant, hashes)
        except module.AuditFailure:
            continue
        raise module.AuditFailure("receipt rejection control accepted")
    return len(mutations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-windows", action="store_true")
    parser.add_argument("--receipt", type=Path, help="write a fresh native receipt here")
    args = parser.parse_args()
    sources, hashes = module.load_sources()
    if os.name != "nt":
        require(not args.require_windows and args.receipt is None,
                "native Windows required; stored receipts do not replace a native replay")
        receipts = [json.loads((PACKAGE / "evidence" / name).read_bytes())
                    for name in ("windows-normal.json", "windows-optimized.json")]
        require([x["optimized"] for x in receipts] == [0, 1], "stored optimization coverage")
        for receipt in receipts:
            check_receipt(receipt, hashes)
            rejection_controls(receipt, hashes)
        print("PASS_STORED_OWNER_DEATH_RECEIPTS_WINDOWS_NOT_RUN controls=5 receipts=2")
        return

    with tempfile.TemporaryDirectory(prefix="owner-death-receipt-") as temporary:
        path = Path(temporary) / "receipt.json"
        # A separate whole-command Job Object bounds even failed fixture startup.
        # It closes only after the worker has recorded all observations/teardown.
        argv = module.python_command("--receipt", path)
        code = sources["reader"].run_windows_command(argv, str(module.ROOT), 180, os.environ.copy())
        require(code == 0, "native audit worker failed: " + str(code))
        receipt = json.loads(path.read_bytes())
        check_receipt(receipt, hashes)
        controls = rejection_controls(receipt, hashes)
        if args.receipt:
            args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("PASS_WINDOWS_STREAM_OWNER_DEATH cases=7 receipt_controls=" + str(controls))


if __name__ == "__main__":
    main()
