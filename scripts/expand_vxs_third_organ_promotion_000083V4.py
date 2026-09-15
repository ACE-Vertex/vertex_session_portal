from __future__ import annotations

from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent.parent
PREDATION = ROOT / "runtime" / "vxs" / "predation"

IR = PREDATION / "powershell-7.6.6-capability-ir.json"
GRAPH = PREDATION / "powershell-7.6.6-capability-graph.json"
PLAN_V1 = PREDATION / "powershell-7.6.6-native-promotion-plan.json"
OUT = PREDATION / "powershell-7.6.6-native-promotion-plan-v2.json"

IR_SCHEMA = "vertex-vxs/powershell-capability-ir-ingestion-1"
GRAPH_SCHEMA = "vertex-vxs/capability-graph-2"
PLAN_V2_SCHEMA = "vertex-vxs/native-promotion-plan-2"

SAFE_AUTHORITIES = {"AUTO_SAFE", "READ", "OBSERVE", "NONE"}
SAFE_SIDE_EFFECTS = {"NONE", "READ_ONLY", "OBSERVE", "NO_SIDE_EFFECT", "NONE_ONLY"}
BLOCKED_ACTIONS = {
    "REMOVE", "DELETE", "SET", "WRITE", "NEW", "CREATE", "START", "STOP",
    "RESTART", "ENABLE", "DISABLE", "INSTALL", "UNINSTALL", "REGISTER",
    "UNREGISTER", "MOUNT", "DISMOUNT", "FORMAT", "CLEAR", "KILL",
    "TERMINATE", "RENAME", "MOVE", "COPY"
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fail(stage: str, code: int, extra: str = "") -> int:
    print("VXS_THIRD_ORGAN_PROMOTION_EXPANSION=FAIL")
    print("STAGE=" + stage)
    if extra:
        print(extra)
    return code

def load_json(path: Path, stage: str, code: int):
    if not path.is_file():
        raise SystemExit(fail(stage + "_LOOKUP", code, "EXPECTED=" + str(path)))
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(
            fail(stage + "_PARSE", code + 1, f"ERROR={type(exc).__name__}:{exc}")
        )

ir = load_json(IR, "IR", 20)
graph = load_json(GRAPH, "GRAPH", 22)
plan_v1 = load_json(PLAN_V1, "PLAN_V1", 24)

if ir.get("schema") not in {IR_SCHEMA, "vertex-vxs/powershell-capability-ir-ingestion-1"}:
    raise SystemExit(fail("IR_SCHEMA", 26, "FOUND=" + str(ir.get("schema"))))

if graph.get("schema") != GRAPH_SCHEMA:
    raise SystemExit(fail("GRAPH_SCHEMA", 27, "FOUND=" + str(graph.get("schema"))))

already_native = {"SYSTEM", "FILESYSTEM"}

native_organs_root = PREDATION / "native-organs"
if native_organs_root.is_dir():
    for manifest_path in native_organs_root.glob("*/organ.json"):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        resource = str(data.get("resource") or "").upper().strip()
        if resource:
            already_native.add(resource)

for ordinal in ("second-organ", "third-organ"):
    folder = PREDATION / ordinal
    if folder.is_dir():
        for selection_path in folder.glob("selection-*.json"):
            try:
                data = json.loads(selection_path.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
            resource = str(
                (data.get("selected") or {}).get("resource") or ""
            ).upper().strip()
            if resource:
                already_native.add(resource)

# Find the IR record array without hardcoding one exact serialization field.
records = None
for key in ("records", "capabilities", "items", "entries", "ir"):
    value = ir.get(key)
    if isinstance(value, list):
        records = value
        break

if records is None:
    # Last-resort structural discovery: choose the largest list-of-dicts.
    list_candidates = []
    for key, value in ir.items():
        if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
            list_candidates.append((len(value), key, value))
    if list_candidates:
        list_candidates.sort(reverse=True)
        records = list_candidates[0][2]

if not isinstance(records, list):
    raise SystemExit(fail("IR_RECORD_DISCOVERY", 28))

def norm(value) -> str:
    return str(value or "").strip().upper()

def pick(record: dict, *keys: str):
    for key in keys:
        if key in record and record.get(key) not in (None, ""):
            return record.get(key)
    return None

def action_tokens(record: dict) -> list[str]:
    raw = pick(record, "action", "ACTION", "verb", "operation")
    if isinstance(raw, list):
        return [norm(x) for x in raw if norm(x)]
    text = norm(raw)
    if not text:
        return []
    return [text]

resource_stats = defaultdict(lambda: {
    "count": 0,
    "safe_count": 0,
    "unsafe_count": 0,
    "actions": Counter(),
    "authorities": Counter(),
    "side_effects": Counter(),
    "semantic_ids": [],
})

usable_records = 0

for index, record in enumerate(records):
    if not isinstance(record, dict):
        continue

    resource = norm(pick(record, "resource", "RESOURCE", "target_resource", "domain"))
    if not resource or resource == "UNKNOWN":
        continue

    actions = action_tokens(record)
    authority = norm(pick(record, "authority", "AUTHORITY", "authority_class"))
    side_effect = norm(pick(record, "side_effect", "SIDE_EFFECT", "effect", "sideEffect"))
    semantic_id = str(
        pick(record, "semantic_id", "semanticId", "id", "capability_id") or index
    )

    blocked_action = any(
        any(blocked == action or blocked in action for blocked in BLOCKED_ACTIONS)
        for action in actions
    )

    authority_safe = (not authority) or authority in SAFE_AUTHORITIES
    side_effect_safe = (not side_effect) or side_effect in SAFE_SIDE_EFFECTS
    safe = authority_safe and side_effect_safe and not blocked_action

    stat = resource_stats[resource]
    stat["count"] += 1
    stat["safe_count"] += int(safe)
    stat["unsafe_count"] += int(not safe)
    for action in actions:
        stat["actions"][action] += 1
    stat["authorities"][authority or "UNKNOWN"] += 1
    stat["side_effects"][side_effect or "UNKNOWN"] += 1
    if len(stat["semantic_ids"]) < 64:
        stat["semantic_ids"].append(semantic_id)

    usable_records += 1

if usable_records == 0 or not resource_stats:
    raise SystemExit(fail("IR_USABLE_RECORDS", 29))

# Incorporate graph support without depending on exact edge serialization.
graph_text = json.dumps(graph, ensure_ascii=False).upper()

candidates = []
for resource, stat in resource_stats.items():
    if resource in already_native:
        continue

    count = stat["count"]
    safe_count = stat["safe_count"]
    unsafe_count = stat["unsafe_count"]
    if safe_count <= 0:
        continue

    safe_ratio = safe_count / max(count, 1)
    graph_mentions = graph_text.count(f'"{resource}"')
    action_diversity = len(stat["actions"])

    # Conservative promotion score:
    # - safety dominates
    # - repeated IR support helps
    # - graph presence helps modestly
    # - unsafe capabilities heavily penalize
    score = (
        safe_ratio * 60.0
        + min(math.log2(safe_count + 1) * 10.0, 20.0)
        + min(graph_mentions, 10) * 1.5
        + min(action_diversity, 5) * 1.0
        - min(unsafe_count, 10) * 4.0
    )

    if safe_ratio >= 0.95 and unsafe_count == 0:
        decision = "PROMOTE_NOW"
    elif safe_ratio >= 0.75:
        decision = "PROMOTE_NEXT"
    else:
        decision = "KEEP_HYBRID"

    candidates.append({
        "resource": resource,
        "decision": decision,
        "score": round(score, 6),
        "record_count": count,
        "safe_count": safe_count,
        "unsafe_count": unsafe_count,
        "safe_ratio": round(safe_ratio, 6),
        "graph_mentions": graph_mentions,
        "actions": [
            {"action": k, "count": v}
            for k, v in stat["actions"].most_common(32)
        ],
        "authorities": dict(stat["authorities"]),
        "side_effects": dict(stat["side_effects"]),
        "sample_semantic_ids": stat["semantic_ids"],
    })

decision_priority = {
    "PROMOTE_NOW": 0,
    "PROMOTE_NEXT": 1,
    "KEEP_HYBRID": 2,
}

candidates.sort(
    key=lambda c: (
        decision_priority.get(c["decision"], 9),
        -float(c["score"]),
        c["resource"],
    )
)

if not candidates:
    raise SystemExit(
        fail(
            "EXPANDED_CANDIDATE_POOL",
            30,
            "CANDIDATE_COUNT=0;EXCLUDED=" + ",".join(sorted(already_native)),
        )
    )

selected = candidates[0]

out_doc = {
    "schema": PLAN_V2_SCHEMA,
    "source_runtime": "PowerShell 7.6.6",
    "generated_from": {
        "capability_ir": str(IR),
        "capability_ir_sha256": sha256_file(IR),
        "capability_graph": str(GRAPH),
        "capability_graph_sha256": sha256_file(GRAPH),
        "previous_plan": str(PLAN_V1),
        "previous_plan_sha256": sha256_file(PLAN_V1),
    },
    "policy": {
        "already_native_resources": sorted(already_native),
        "safe_authorities": sorted(SAFE_AUTHORITIES),
        "safe_side_effects": sorted(SAFE_SIDE_EFFECTS),
        "blocked_actions": sorted(BLOCKED_ACTIONS),
        "principle": "safe-read-observe-first; mutation remains Human Gate or PowerShell backend",
    },
    "candidate_count": len(candidates),
    "selected_third_organ_candidate": selected,
    "candidates": candidates,
}

# Persist only after complete analysis succeeds.
OUT.write_text(
    json.dumps(out_doc, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

persisted = json.loads(OUT.read_text(encoding="utf-8"))
if persisted.get("schema") != PLAN_V2_SCHEMA:
    raise SystemExit(fail("PERSISTED_SCHEMA", 31))
if persisted.get("candidate_count", 0) < 1:
    raise SystemExit(fail("PERSISTED_CANDIDATES", 32))
if (
    (persisted.get("selected_third_organ_candidate") or {}).get("resource")
    != selected["resource"]
):
    raise SystemExit(fail("PERSISTED_SELECTION", 33))

print("VXS_THIRD_ORGAN_PROMOTION_EXPANSION=PASS")
print("IR_RECORD_COUNT=" + str(len(records)))
print("IR_USABLE_RECORDS=" + str(usable_records))
print("RESOURCE_COUNT=" + str(len(resource_stats)))
print("EXCLUDED_RESOURCES=" + ",".join(sorted(already_native)))
print("EXPANDED_CANDIDATE_COUNT=" + str(len(candidates)))
print("SELECTED_RESOURCE=" + selected["resource"])
print("SELECTED_DECISION=" + selected["decision"])
print("SELECTED_SCORE=" + str(selected["score"]))
print("SELECTED_SAFE_COUNT=" + str(selected["safe_count"]))
print("SELECTED_UNSAFE_COUNT=" + str(selected["unsafe_count"]))
print("SELECTED_SAFE_RATIO=" + str(selected["safe_ratio"]))
print("PLAN_V2_PATH=" + str(OUT))
print("PLAN_V2_SHA256=" + sha256_file(OUT))
print("MUTATION_CAPABILITIES_NATIVE_PROMOTED=false")
print("HUMAN_GATE_PRESERVED=true")
print("POWERSHELL_BACKEND_PRESERVED=true")
raise SystemExit(0)
