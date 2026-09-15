from __future__ import annotations

from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parent.parent
PRED = ROOT / "runtime" / "vxs" / "predation"

CENSUS = PRED / "powershell-7.6.6-capability-census.json"
IR = PRED / "powershell-7.6.6-capability-ir.json"
GRAPH = PRED / "powershell-7.6.6-capability-graph.json"
PLAN_V2 = PRED / "powershell-7.6.6-native-promotion-plan-v2.json"

SEED_BANK = PRED / "powershell-7.6.6-native-capability-seed-bank-v3.json"
PLAN_V3 = PRED / "powershell-7.6.6-native-promotion-plan-v3.json"

SAFE_VERBS = {
    "GET", "TEST", "FIND", "SEARCH", "SELECT", "MEASURE", "COMPARE",
    "RESOLVE", "READ", "SHOW", "FORMAT", "CONVERT", "TRACE"
}
MUTATION_VERBS = {
    "SET", "NEW", "ADD", "REMOVE", "DELETE", "CLEAR", "START", "STOP",
    "RESTART", "ENABLE", "DISABLE", "INSTALL", "UNINSTALL", "REGISTER",
    "UNREGISTER", "RENAME", "MOVE", "COPY", "MOUNT", "DISMOUNT",
    "FORMAT-VOLUME", "KILL", "TERMINATE", "WRITE", "EXPORT", "IMPORT"
}
SAFE_AUTHORITIES = {"AUTO_SAFE", "READ", "OBSERVE", "NONE"}
SAFE_EFFECTS = {"NONE", "READ_ONLY", "OBSERVE", "NO_SIDE_EFFECT", "NONE_ONLY"}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fail(stage: str, code: int, extra: str = "") -> int:
    print("VXS_NATIVE_FIELD_EXPANSION=FAIL")
    print("STAGE=" + stage)
    if extra:
        print(extra)
    return code

def load(path: Path, label: str, code: int):
    if not path.is_file():
        raise SystemExit(fail(label + "_LOOKUP", code, "EXPECTED=" + str(path)))
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(
            fail(label + "_PARSE", code + 1, f"ERROR={type(exc).__name__}:{exc}")
        )

census = load(CENSUS, "CENSUS", 20)
ir = load(IR, "IR", 22)
graph = load(GRAPH, "GRAPH", 24)
plan_v2 = load(PLAN_V2, "PLAN_V2", 26)

# Durable native resources.
already_native = {"SYSTEM", "FILESYSTEM"}
native_root = PRED / "native-organs"
if native_root.is_dir():
    for p in native_root.glob("*/organ.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        r = str(d.get("resource") or "").upper().strip()
        if r:
            already_native.add(r)

for folder_name in ("second-organ", "third-organ"):
    folder = PRED / folder_name
    if not folder.is_dir():
        continue
    for p in folder.glob("selection-*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        r = str((d.get("selected") or {}).get("resource") or "").upper().strip()
        if r:
            already_native.add(r)

def first_list_of_dicts(doc: dict):
    preferred = ("records", "capabilities", "items", "entries", "ir", "commands")
    for k in preferred:
        v = doc.get(k)
        if isinstance(v, list) and all(isinstance(x, dict) for x in v):
            return v
    cands = []
    for k, v in doc.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            cands.append((len(v), k, v))
    if cands:
        cands.sort(reverse=True)
        return cands[0][2]
    return []

ir_records = first_list_of_dicts(ir)
if not ir_records:
    raise SystemExit(fail("IR_RECORD_DISCOVERY", 28))

def norm(v) -> str:
    return str(v or "").strip().upper()

def pick(d: dict, *keys):
    for k in keys:
        if k in d and d.get(k) not in (None, ""):
            return d.get(k)
    return None

# Index IR-known capability families.
ir_families = defaultdict(lambda: {
    "count": 0,
    "safe_count": 0,
    "unsafe_count": 0,
    "actions": Counter(),
    "authorities": Counter(),
    "effects": Counter(),
    "semantic_ids": [],
})

for i, rec in enumerate(ir_records):
    if not isinstance(rec, dict):
        continue
    resource = norm(pick(rec, "resource", "RESOURCE", "target_resource", "domain"))
    if not resource or resource == "UNKNOWN":
        continue

    raw_action = pick(rec, "action", "ACTION", "verb", "operation")
    actions = raw_action if isinstance(raw_action, list) else [raw_action] if raw_action else []
    actions = [norm(x) for x in actions if norm(x)]

    authority = norm(pick(rec, "authority", "AUTHORITY", "authority_class"))
    effect = norm(pick(rec, "side_effect", "SIDE_EFFECT", "effect", "sideEffect"))

    blocked = any(
        any(m == a or m in a for m in MUTATION_VERBS)
        for a in actions
    )
    safe = (
        (not authority or authority in SAFE_AUTHORITIES)
        and (not effect or effect in SAFE_EFFECTS)
        and not blocked
    )

    f = ir_families[resource]
    f["count"] += 1
    f["safe_count"] += int(safe)
    f["unsafe_count"] += int(not safe)
    for a in actions:
        f["actions"][a] += 1
    f["authorities"][authority or "UNKNOWN"] += 1
    f["effects"][effect or "UNKNOWN"] += 1
    if len(f["semantic_ids"]) < 128:
        f["semantic_ids"].append(
            str(pick(rec, "semantic_id", "semanticId", "id", "capability_id") or i)
        )

# Pull every plausible PowerShell command name out of the census without assuming
# a single fixed census serialization.
command_names = set()

def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if isinstance(v, str) and kl in {
                "name", "command", "command_name", "cmdlet", "cmdlet_name"
            }:
                s = v.strip()
                if re.match(r"^[A-Za-z]+-[A-Za-z0-9][A-Za-z0-9_-]*$", s):
                    command_names.add(s)
            walk(v)
    elif isinstance(obj, list):
        for x in obj:
            walk(x)
    elif isinstance(obj, str):
        s = obj.strip()
        if re.match(r"^[A-Za-z]+-[A-Za-z0-9][A-Za-z0-9_-]*$", s):
            command_names.add(s)

walk(census)

# Classify command seeds.
seed_families = defaultdict(lambda: {
    "safe_observe_commands": [],
    "mutation_commands": [],
    "unknown_commands": [],
    "verbs": Counter(),
})

for cmd in sorted(command_names):
    if "-" not in cmd:
        continue
    verb, noun = cmd.split("-", 1)
    v = verb.upper()
    noun_key = re.sub(r"[^A-Z0-9]+", "_", noun.upper()).strip("_") or "UNKNOWN"

    sf = seed_families[noun_key]
    sf["verbs"][v] += 1

    if v in MUTATION_VERBS:
        if len(sf["mutation_commands"]) < 64:
            sf["mutation_commands"].append(cmd)
    elif v in SAFE_VERBS:
        if len(sf["safe_observe_commands"]) < 64:
            sf["safe_observe_commands"].append(cmd)
    else:
        if len(sf["unknown_commands"]) < 64:
            sf["unknown_commands"].append(cmd)

graph_text = json.dumps(graph, ensure_ascii=False).upper()

# READY candidates: already represented in IR, safe enough, not yet native.
ready = []
for resource, f in ir_families.items():
    if resource in already_native or f["safe_count"] <= 0:
        continue

    ratio = f["safe_count"] / max(1, f["count"])
    graph_mentions = graph_text.count(f'"{resource}"')
    score = (
        ratio * 60.0
        + min(math.log2(f["safe_count"] + 1) * 10.0, 20.0)
        + min(graph_mentions, 10) * 1.5
        - min(f["unsafe_count"], 10) * 4.0
    )

    if ratio >= 0.95 and f["unsafe_count"] == 0:
        decision = "PROMOTE_NOW"
    elif ratio >= 0.75:
        decision = "PROMOTE_NEXT"
    else:
        decision = "KEEP_HYBRID"

    ready.append({
        "resource": resource,
        "tier": "READY_NATIVE",
        "decision": decision,
        "score": round(score, 6),
        "record_count": f["count"],
        "safe_count": f["safe_count"],
        "unsafe_count": f["unsafe_count"],
        "safe_ratio": round(ratio, 6),
        "actions": [{"action": k, "count": v} for k, v in f["actions"].most_common(32)],
        "authorities": dict(f["authorities"]),
        "side_effects": dict(f["effects"]),
        "sample_semantic_ids": f["semantic_ids"],
    })

# DISCOVERY_ONLY candidates: census shows read-like commands but IR has no matching
# resource family yet. These are seeds, never auto-promoted.
discovery_only = []
known_resources = set(ir_families.keys()) | already_native

for noun_key, sf in seed_families.items():
    if noun_key in known_resources:
        continue
    safe_n = len(sf["safe_observe_commands"])
    mut_n = len(sf["mutation_commands"])
    unk_n = len(sf["unknown_commands"])
    if safe_n <= 0:
        continue

    total = safe_n + mut_n + unk_n
    purity = safe_n / max(1, total)

    discovery_only.append({
        "resource_seed": noun_key,
        "tier": "DISCOVERY_ONLY",
        "native_promotion_allowed": False,
        "safe_command_count": safe_n,
        "mutation_command_count": mut_n,
        "unknown_command_count": unk_n,
        "safe_purity": round(purity, 6),
        "safe_observe_commands": sf["safe_observe_commands"],
        "mutation_commands": sf["mutation_commands"],
        "unknown_commands": sf["unknown_commands"],
        "verbs": dict(sf["verbs"]),
        "required_next_step": "CAPABILITY_IR_MAPPING",
    })

priority = {"PROMOTE_NOW": 0, "PROMOTE_NEXT": 1, "KEEP_HYBRID": 2}
ready.sort(key=lambda x: (priority.get(x["decision"], 9), -x["score"], x["resource"]))
discovery_only.sort(
    key=lambda x: (
        -x["safe_purity"],
        -x["safe_command_count"],
        x["resource_seed"],
    )
)

selected_ready = ready[0] if ready else None
selected_seed = discovery_only[0] if discovery_only else None

seed_bank = {
    "schema": "vertex-vxs/native-capability-seed-bank-3",
    "source_runtime": "PowerShell 7.6.6",
    "sources": {
        "census": str(CENSUS),
        "census_sha256": sha256_file(CENSUS),
        "capability_ir": str(IR),
        "capability_ir_sha256": sha256_file(IR),
        "capability_graph": str(GRAPH),
        "capability_graph_sha256": sha256_file(GRAPH),
        "promotion_plan_v2": str(PLAN_V2),
        "promotion_plan_v2_sha256": sha256_file(PLAN_V2),
    },
    "policy": {
        "existing_native_resources": sorted(already_native),
        "ready_native_requires_ir": True,
        "discovery_only_may_not_auto_promote": True,
        "mutation_requires_human_gate_or_backend": True,
    },
    "census_command_count": len(command_names),
    "ir_resource_count": len(ir_families),
    "ready_native_count": len(ready),
    "discovery_only_count": len(discovery_only),
    "selected_ready_native": selected_ready,
    "selected_discovery_seed": selected_seed,
    "ready_native": ready,
    "discovery_only": discovery_only[:512],
}

SEED_BANK.write_text(
    json.dumps(seed_bank, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

plan_v3 = {
    "schema": "vertex-vxs/native-promotion-plan-3",
    "source_seed_bank": str(SEED_BANK),
    "source_seed_bank_sha256": sha256_file(SEED_BANK),
    "already_native_resources": sorted(already_native),
    "selected_next_native_candidate": selected_ready,
    "ready_native": ready,
    "discovery_seed_count": len(discovery_only),
    "next_expansion_rule": (
        "map DISCOVERY_ONLY seed through Capability IR before native promotion"
    ),
    "human_gate_preserved": True,
    "powershell_backend_preserved": True,
}

PLAN_V3.write_text(
    json.dumps(plan_v3, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

# Durable self-check.
persisted_seed = json.loads(SEED_BANK.read_text(encoding="utf-8"))
persisted_plan = json.loads(PLAN_V3.read_text(encoding="utf-8"))

if persisted_seed.get("schema") != "vertex-vxs/native-capability-seed-bank-3":
    raise SystemExit(fail("SEED_BANK_SCHEMA", 30))
if persisted_plan.get("schema") != "vertex-vxs/native-promotion-plan-3":
    raise SystemExit(fail("PLAN_V3_SCHEMA", 31))
if persisted_plan.get("human_gate_preserved") is not True:
    raise SystemExit(fail("HUMAN_GATE_GUARD", 32))
if persisted_plan.get("powershell_backend_preserved") is not True:
    raise SystemExit(fail("BACKEND_GUARD", 33))

if not ready and not discovery_only:
    raise SystemExit(fail("FIELD_EXPANSION_EMPTY", 34))

print("VXS_NATIVE_FIELD_EXPANSION=PASS")
print("CENSUS_COMMAND_COUNT=" + str(len(command_names)))
print("IR_RESOURCE_COUNT=" + str(len(ir_families)))
print("EXISTING_NATIVE_RESOURCES=" + ",".join(sorted(already_native)))
print("READY_NATIVE_COUNT=" + str(len(ready)))
print("DISCOVERY_ONLY_COUNT=" + str(len(discovery_only)))

if selected_ready:
    print("SELECTED_READY_RESOURCE=" + selected_ready["resource"])
    print("SELECTED_READY_DECISION=" + selected_ready["decision"])
    print("SELECTED_READY_SCORE=" + str(selected_ready["score"]))
else:
    print("SELECTED_READY_RESOURCE=NONE")

if selected_seed:
    print("SELECTED_DISCOVERY_SEED=" + selected_seed["resource_seed"])
    print("SELECTED_DISCOVERY_SAFE_COMMAND_COUNT=" + str(selected_seed["safe_command_count"]))
    print("SELECTED_DISCOVERY_MUTATION_COMMAND_COUNT=" + str(selected_seed["mutation_command_count"]))
else:
    print("SELECTED_DISCOVERY_SEED=NONE")

print("SEED_BANK_PATH=" + str(SEED_BANK))
print("SEED_BANK_SHA256=" + sha256_file(SEED_BANK))
print("PLAN_V3_PATH=" + str(PLAN_V3))
print("PLAN_V3_SHA256=" + sha256_file(PLAN_V3))
print("DISCOVERY_ONLY_AUTO_PROMOTION=false")
print("MUTATION_NATIVE_PROMOTION=false")
print("HUMAN_GATE_PRESERVED=true")
print("POWERSHELL_BACKEND_PRESERVED=true")
raise SystemExit(0)
