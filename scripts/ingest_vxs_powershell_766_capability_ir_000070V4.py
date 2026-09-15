from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import sys
from typing import Any

IR_SCHEMA = "vxs-capability-ir/1"
INGEST_SCHEMA = "vertex-vxs/powershell-capability-ir-ingestion-1"
CENSUS_SCHEMA = "vertex-vxs/powershell-capability-census-1"
EXPECTED_PS_VERSION = "7.6.6"

ACTION_MAP = {
    "Get": "OBSERVE",
    "Test": "TEST",
    "Find": "FIND",
    "Search": "FIND",
    "Measure": "MEASURE",
    "Compare": "COMPARE",
    "Resolve": "RESOLVE",
    "New": "CREATE",
    "Set": "UPDATE",
    "Add": "ADD",
    "Start": "START",
    "Stop": "STOP",
    "Restart": "RESTART",
    "Remove": "REMOVE",
    "Clear": "REMOVE",
    "Unregister": "REMOVE",
    "Uninstall": "REMOVE",
    "Enable": "ENABLE",
    "Disable": "DISABLE",
    "Install": "INSTALL",
    "Register": "INSTALL",
    "Update": "UPDATE",
    "Move": "MOVE",
    "Rename": "RENAME",
    "Copy": "COPY",
    "Import": "IMPORT",
    "Export": "EXPORT",
    "Write": "WRITE",
    "Out": "WRITE",
    "Invoke": "INVOKE",
}

RESOURCE_RULES = [
    (re.compile(r"(Process)", re.I), "PROCESS"),
    (re.compile(r"(Service)", re.I), "SERVICE"),
    (re.compile(r"(Net|Tcp|Udp|Dns|IP|Route|Adapter|Connection|Firewall|Proxy)", re.I), "NETWORK"),
    (re.compile(r"(Registry)", re.I), "REGISTRY"),
    (re.compile(r"(Acl|Authenticode|ExecutionPolicy|Credential|Certificate|Secret)", re.I), "SECURITY"),
    (re.compile(r"(Cim|Wmi|Computer|Host|System|OperatingSystem)", re.I), "SYSTEM"),
    (re.compile(r"(Event|WinEvent|EventLog)", re.I), "EVENTLOG"),
    (re.compile(r"(ScheduledTask|Job)", re.I), "JOB"),
    (re.compile(r"(Module|Command|Alias|Variable|Function|PSDrive|PSProvider)", re.I), "SHELL"),
    (re.compile(r"(Package|Appx)", re.I), "PACKAGE"),
    (re.compile(r"(Printer)", re.I), "PRINTER"),
    (re.compile(r"(Item|ChildItem|Content|Path|Location|File|Directory)", re.I), "FILESYSTEM"),
]

TARGET_PARAM_NAMES = {
    "Name", "Path", "LiteralPath", "Id", "ProcessName", "ServiceName",
    "ComputerName", "Destination", "DestinationPath", "Source", "SourcePath",
    "Module", "ModuleName", "CommandName", "ClassName", "Namespace",
    "InputObject", "Uri", "Address", "InterfaceAlias", "InterfaceIndex",
    "InstanceId", "Key", "Property", "UserName",
}

DISRUPTIVE_ACTIONS = {"STOP", "RESTART", "DISABLE"}
DESTRUCTIVE_ACTIONS = {"REMOVE"}
MUTATING_ACTIONS = {
    "CREATE", "UPDATE", "ADD", "START", "ENABLE", "INSTALL", "MOVE", "RENAME",
    "COPY", "IMPORT", "EXPORT", "WRITE", "INVOKE",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_resource(command: dict[str, Any]) -> str:
    text = " ".join(
        str(command.get(k) or "")
        for k in ("noun", "name", "module_name", "source")
    )
    for rx, resource in RESOURCE_RULES:
        if rx.search(text):
            return resource

    noun = str(command.get("noun") or "").strip()
    if noun:
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", noun).upper()
        snake = re.sub(r"[^A-Z0-9_]+", "_", snake).strip("_")
        if snake:
            return snake
    return "UNKNOWN"


def normalize_action(command: dict[str, Any]) -> str:
    verb = str(command.get("verb") or "").strip()
    if not verb:
        return "UNKNOWN"
    return ACTION_MAP.get(verb, re.sub(r"[^A-Za-z0-9]+", "_", verb).upper())


def flatten_parameters(command: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for ps in command.get("parameter_sets") or []:
        for p in ps.get("parameters") or []:
            name = str(p.get("name") or "").strip()
            if name:
                names.add(name)
    return sorted(names, key=str.lower)


def target_hints(parameters: list[str]) -> list[str]:
    hinted = [p for p in parameters if p in TARGET_PARAM_NAMES]
    return hinted[:16]


def classify_side_effect(action: str, authority: str) -> str:
    if authority == "AUTO_SAFE":
        return "NONE"
    if action in DISRUPTIVE_ACTIONS:
        return "DISRUPTIVE"
    if action in DESTRUCTIVE_ACTIONS:
        return "DESTRUCTIVE"
    if action in MUTATING_ACTIONS:
        return "MUTATING"
    return "UNKNOWN_MUTATION"


def build_ir(command: dict[str, Any], source_sha256: str, ps_version: str) -> dict[str, Any]:
    action = normalize_action(command)
    resource = normalize_resource(command)
    parameters = flatten_parameters(command)

    authority = str(command.get("authority_candidate") or "HUMAN_APPLY")
    if authority not in {"AUTO_SAFE", "HUMAN_APPLY"}:
        authority = "HUMAN_APPLY"

    if command.get("supports_should_process"):
        authority = "HUMAN_APPLY"

    side_effect = classify_side_effect(action, authority)
    hints = target_hints(parameters)

    command_name = str(command.get("name") or "")
    module_name = str(command.get("module_name") or "")
    source_id = f"{module_name}:{command_name}" if module_name else command_name
    capability_id = "ps:" + re.sub(r"[^a-z0-9._:-]+", "-", source_id.lower()).strip("-")

    return {
        "schema": IR_SCHEMA,
        "capability_id": capability_id,
        "provider": "powershell",
        "action": action,
        "resource": resource,
        "target": {
            "kind": "PARAMETERIZED" if hints else "IMPLICIT_CONTEXT",
            "parameter_hints": hints,
        },
        "parameters": parameters,
        "side_effect": side_effect,
        "authority": authority,
        "safety_reason": (
            "Census classified as read-only safe and command does not advertise ShouldProcess."
            if authority == "AUTO_SAFE"
            else "Requires HUMAN_APPLY because mutation/disruption risk, ShouldProcess support, or non-read-only semantics."
        ),
        "source": {
            "runtime": "powershell",
            "runtime_version": ps_version,
            "command_name": command_name,
            "command_type": command.get("command_type"),
            "module_name": module_name,
            "command_version": command.get("version"),
            "verb": command.get("verb"),
            "noun": command.get("noun"),
            "supports_should_process": bool(command.get("supports_should_process")),
            "confirm_impact": command.get("confirm_impact"),
            "census_sha256": source_sha256,
        },
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    predation_dir = root / "runtime" / "vxs" / "predation"
    census_path = predation_dir / f"powershell-{EXPECTED_PS_VERSION}-capability-census.json"

    if not census_path.is_file():
        print("VXS_IR_INGEST=FAIL")
        print("STAGE=CENSUS_LOOKUP")
        print("EXPECTED=" + str(census_path))
        return 20

    source_sha = sha256_file(census_path)

    try:
        census = json.loads(census_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print("VXS_IR_INGEST=FAIL")
        print("STAGE=CENSUS_PARSE")
        print("ERROR=" + type(exc).__name__ + ":" + str(exc))
        return 21

    if census.get("schema") != CENSUS_SCHEMA:
        print("VXS_IR_INGEST=FAIL")
        print("STAGE=CENSUS_SCHEMA")
        print("FOUND=" + str(census.get("schema")))
        return 22

    runtime = census.get("runtime") or {}
    ps_version = str(runtime.get("ps_version") or "")
    if ps_version != EXPECTED_PS_VERSION:
        print("VXS_IR_INGEST=FAIL")
        print("STAGE=RUNTIME_VERSION")
        print("FOUND=" + ps_version)
        return 23

    commands = census.get("commands") or []
    if not isinstance(commands, list) or not commands:
        print("VXS_IR_INGEST=FAIL")
        print("STAGE=COMMANDS_EMPTY")
        return 24

    ir_records = [build_ir(cmd, source_sha, ps_version) for cmd in commands]

    ids = [r["capability_id"] for r in ir_records]
    duplicate_ids = sorted(k for k, v in Counter(ids).items() if v > 1)

    authority_counts = Counter(r["authority"] for r in ir_records)
    action_counts = Counter(r["action"] for r in ir_records)
    resource_counts = Counter(r["resource"] for r in ir_records)
    side_effect_counts = Counter(r["side_effect"] for r in ir_records)

    out_path = predation_dir / f"powershell-{ps_version}-capability-ir.json"
    document = {
        "schema": INGEST_SCHEMA,
        "generated_from": {
            "path": str(census_path),
            "sha256": source_sha,
            "schema": census.get("schema"),
            "runtime_version": ps_version,
        },
        "summary": {
            "input_command_count": len(commands),
            "ir_record_count": len(ir_records),
            "duplicate_capability_id_count": len(duplicate_ids),
            "authority_counts": dict(sorted(authority_counts.items())),
            "side_effect_counts": dict(sorted(side_effect_counts.items())),
            "top_actions": action_counts.most_common(20),
            "top_resources": resource_counts.most_common(20),
        },
        "duplicate_capability_ids": duplicate_ids[:100],
        "capabilities": ir_records,
    }

    predation_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    out_sha = sha256_file(out_path)
    out_bytes = out_path.stat().st_size

    # Verify what was just written, not only the in-memory document.
    persisted = json.loads(out_path.read_text(encoding="utf-8"))
    if persisted.get("schema") != INGEST_SCHEMA:
        print("VXS_IR_INGEST=FAIL")
        print("STAGE=PERSISTED_SCHEMA")
        return 30
    if len(persisted.get("capabilities") or []) != len(commands):
        print("VXS_IR_INGEST=FAIL")
        print("STAGE=PERSISTED_COUNT")
        return 31

    print("VXS_IR_INGEST=PASS")
    print("PS_VERSION=" + ps_version)
    print("CENSUS_SHA256=" + source_sha)
    print("INPUT_COMMAND_COUNT=" + str(len(commands)))
    print("IR_RECORD_COUNT=" + str(len(ir_records)))
    print("DUPLICATE_ID_COUNT=" + str(len(duplicate_ids)))
    print("AUTO_SAFE_COUNT=" + str(authority_counts.get("AUTO_SAFE", 0)))
    print("HUMAN_APPLY_COUNT=" + str(authority_counts.get("HUMAN_APPLY", 0)))
    print("IR_PATH=" + str(out_path))
    print("IR_BYTES=" + str(out_bytes))
    print("IR_SHA256=" + out_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
