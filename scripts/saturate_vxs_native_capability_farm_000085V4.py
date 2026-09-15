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
SEED_V3 = PRED / "powershell-7.6.6-native-capability-seed-bank-v3.json"
PLAN_V3 = PRED / "powershell-7.6.6-native-promotion-plan-v3.json"

FARM_V4 = PRED / "powershell-7.6.6-native-capability-farm-v4.json"
IR_QUEUE_V4 = PRED / "powershell-7.6.6-ir-maturation-queue-v4.json"
WAVE_V4 = PRED / "powershell-7.6.6-native-promotion-wave-v4.json"
SAT_V4 = PRED / "powershell-7.6.6-native-saturation-report-v4.json"

SAFE_VERBS = {
    "GET", "TEST", "FIND", "SEARCH", "SELECT", "MEASURE", "COMPARE",
    "RESOLVE", "READ", "SHOW", "FORMAT", "CONVERT", "TRACE", "WATCH"
}
MUTATION_VERBS = {
    "SET", "NEW", "ADD", "REMOVE", "DELETE", "CLEAR", "START", "STOP",
    "RESTART", "ENABLE", "DISABLE", "INSTALL", "UNINSTALL", "REGISTER",
    "UNREGISTER", "RENAME", "MOVE", "COPY", "MOUNT", "DISMOUNT",
    "FORMAT", "KILL", "TERMINATE", "WRITE", "EXPORT", "IMPORT", "PUBLISH"
}

def fail(stage: str, code: int, extra: str = "") -> int:
    print("VXS_NATIVE_FARM_SATURATION=FAIL")
    print("STAGE=" + stage)
    if extra:
        print(extra)
    return code

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load(path: Path, label: str, code: int):
    if not path.is_file():
        raise SystemExit(fail(label + "_LOOKUP", code, "EXPECTED=" + str(path)))
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise SystemExit(
            fail(label + "_PARSE", code + 1, f"ERROR={type(exc).__name__}:{exc}")
        )

def norm(v) -> str:
    return str(v or "").strip().upper()

def walk_commands(obj, out_set: set[str]):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if isinstance(v, str) and kl in {
                "name", "command", "command_name", "cmdlet", "cmdlet_name"
            }:
                s = v.strip()
                if re.match(r"^[A-Za-z]+-[A-Za-z0-9][A-Za-z0-9_-]*$", s):
                    out_set.add(s)
            walk_commands(v, out_set)
    elif isinstance(obj, list):
        for x in obj:
            walk_commands(x, out_set)
    elif isinstance(obj, str):
        s = obj.strip()
        if re.match(r"^[A-Za-z]+-[A-Za-z0-9][A-Za-z0-9_-]*$", s):
            out_set.add(s)

census = load(CENSUS, "CENSUS", 20)
ir = load(IR, "IR", 22)
graph = load(GRAPH, "GRAPH", 24)
plan_v2 = load(PLAN_V2, "PLAN_V2", 26)
seed_v3 = load(SEED_V3, "SEED_V3", 28)
plan_v3 = load(PLAN_V3, "PLAN_V3", 30)

if seed_v3.get("schema") != "vertex-vxs/native-capability-seed-bank-3":
    raise SystemExit(fail("SEED_V3_SCHEMA", 32, "FOUND=" + str(seed_v3.get("schema"))))
if plan_v3.get("schema") != "vertex-vxs/native-promotion-plan-3":
    raise SystemExit(fail("PLAN_V3_SCHEMA", 33, "FOUND=" + str(plan_v3.get("schema"))))

already_native = set(str(x).upper() for x in plan_v3.get("already_native_resources", []) if str(x).strip())
native_root = PRED / "native-organs"
if native_root.is_dir():
    for p in native_root.glob("*/organ.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        resource = norm(d.get("resource"))
        if resource:
            already_native.add(resource)

ready = []
for row in seed_v3.get("ready_native", []):
    if not isinstance(row, dict):
        continue
    resource = norm(row.get("resource"))
    if not resource or resource in already_native:
        continue
    item = dict(row)
    item["resource"] = resource
    ready.append(item)

discovery = []
for row in seed_v3.get("discovery_only", []):
    if not isinstance(row, dict):
        continue
    seed = norm(row.get("resource_seed"))
    if not seed or seed in already_native:
        continue
    item = dict(row)
    item["resource_seed"] = seed
    discovery.append(item)

# Re-census commands to detect inventory not represented by the V3 seed bank.
census_commands = set()
walk_commands(census, census_commands)

seed_bank_commands = set()
for row in discovery:
    for key in ("safe_observe_commands", "mutation_commands", "unknown_commands"):
        for cmd in row.get(key, []) or []:
            if isinstance(cmd, str) and cmd.strip():
                seed_bank_commands.add(cmd.strip())

unbanked_commands = sorted(census_commands - seed_bank_commands)

# Classify unbanked commands conservatively. They remain DISCOVERY_ONLY.
unbanked_by_noun = defaultdict(lambda: {
    "safe": [],
    "mutation": [],
    "unknown": [],
    "verbs": Counter(),
})

for cmd in unbanked_commands:
    if "-" not in cmd:
        continue
    verb, noun = cmd.split("-", 1)
    v = verb.upper()
    noun_key = re.sub(r"[^A-Z0-9]+", "_", noun.upper()).strip("_") or "UNKNOWN"
    bucket = unbanked_by_noun[noun_key]
    bucket["verbs"][v] += 1
    if v in MUTATION_VERBS:
        bucket["mutation"].append(cmd)
    elif v in SAFE_VERBS:
        bucket["safe"].append(cmd)
    else:
        bucket["unknown"].append(cmd)

extra_discovery = []
known_seeds = {norm(x.get("resource_seed")) for x in discovery}
for noun_key, bucket in unbanked_by_noun.items():
    if noun_key in known_seeds or noun_key in already_native:
        continue
    if not bucket["safe"]:
        continue
    total = len(bucket["safe"]) + len(bucket["mutation"]) + len(bucket["unknown"])
    purity = len(bucket["safe"]) / max(1, total)
    extra_discovery.append({
        "resource_seed": noun_key,
        "tier": "DISCOVERY_ONLY",
        "native_promotion_allowed": False,
        "safe_command_count": len(bucket["safe"]),
        "mutation_command_count": len(bucket["mutation"]),
        "unknown_command_count": len(bucket["unknown"]),
        "safe_purity": round(purity, 6),
        "safe_observe_commands": bucket["safe"][:128],
        "mutation_commands": bucket["mutation"][:128],
        "unknown_commands": bucket["unknown"][:128],
        "verbs": dict(bucket["verbs"]),
        "required_next_step": "CAPABILITY_IR_MAPPING",
        "source": "SATURATION_RECENSUS",
    })

discovery.extend(extra_discovery)

# IR maturation queue: only clean seeds become mapping-ready; still not native.
ir_queue = []
for row in discovery:
    safe_n = int(row.get("safe_command_count", 0) or 0)
    mut_n = int(row.get("mutation_command_count", 0) or 0)
    unk_n = int(row.get("unknown_command_count", 0) or 0)
    purity = float(row.get("safe_purity", 0.0) or 0.0)

    if mut_n == 0 and safe_n >= 3 and purity >= 0.90:
        state = "IR_MAPPING_READY"
        priority = 0
    elif mut_n == 0 and safe_n >= 1 and purity >= 0.75:
        state = "IR_MAPPING_CANDIDATE"
        priority = 1
    else:
        state = "RESEARCH_REQUIRED"
        priority = 2

    score = (
        purity * 70.0
        + min(math.log2(safe_n + 1) * 10.0, 20.0)
        - min(mut_n, 10) * 8.0
        - min(unk_n, 10) * 2.0
    )

    ir_queue.append({
        "resource_seed": row["resource_seed"],
        "state": state,
        "priority": priority,
        "score": round(score, 6),
        "safe_command_count": safe_n,
        "mutation_command_count": mut_n,
        "unknown_command_count": unk_n,
        "safe_purity": purity,
        "safe_observe_commands": list(row.get("safe_observe_commands", []) or []),
        "native_promotion_allowed": False,
    })

ir_queue.sort(key=lambda x: (x["priority"], -x["score"], x["resource_seed"]))

# Native promotion wave from READY_NATIVE only.
decision_priority = {"PROMOTE_NOW": 0, "PROMOTE_NEXT": 1, "KEEP_HYBRID": 2}
ready.sort(
    key=lambda x: (
        decision_priority.get(str(x.get("decision", "")).upper(), 9),
        -float(x.get("score", 0.0) or 0.0),
        x["resource"],
    )
)

# Saturation waves are planning only. Workstation remains allocation authority.
waves = []
wave_size = 8
for i in range(0, len(ready), wave_size):
    batch = ready[i:i + wave_size]
    waves.append({
        "wave": len(waves) + 1,
        "candidate_count": len(batch),
        "resources": [
            {
                "resource": x["resource"],
                "decision": x.get("decision"),
                "score": x.get("score"),
                "safe_ratio": x.get("safe_ratio"),
            }
            for x in batch
        ],
        "execution_authority": "HUMAN_APPLY_REQUIRED_PER_ISSUANCE",
        "lane_allocation_authority": "VERTEX_WORKSTATION",
    })

mapping_ready = [x for x in ir_queue if x["state"] == "IR_MAPPING_READY"]
mapping_candidate = [x for x in ir_queue if x["state"] == "IR_MAPPING_CANDIDATE"]
research_required = [x for x in ir_queue if x["state"] == "RESEARCH_REQUIRED"]

# A bounded engineering saturation indicator, not a claim of completeness.
known_surface = len(already_native) + len(ready) + len(discovery)
resolved_surface = len(already_native) + len(ready) + len(mapping_ready)
saturation_ratio = resolved_surface / max(1, known_surface)

farm_doc = {
    "schema": "vertex-vxs/native-capability-farm-4",
    "runtime": "PowerShell 7.6.6",
    "sources": {
        "census": {"path": str(CENSUS), "sha256": sha256_file(CENSUS)},
        "capability_ir": {"path": str(IR), "sha256": sha256_file(IR)},
        "capability_graph": {"path": str(GRAPH), "sha256": sha256_file(GRAPH)},
        "promotion_plan_v2": {"path": str(PLAN_V2), "sha256": sha256_file(PLAN_V2)},
        "seed_bank_v3": {"path": str(SEED_V3), "sha256": sha256_file(SEED_V3)},
        "promotion_plan_v3": {"path": str(PLAN_V3), "sha256": sha256_file(PLAN_V3)},
    },
    "existing_native_resources": sorted(already_native),
    "ready_native": ready,
    "discovery_only": discovery,
    "ir_maturation_queue": ir_queue,
    "policy": {
        "human_gate_preserved": True,
        "powershell_backend_preserved": True,
        "mutation_native_auto_promotion": False,
        "discovery_only_native_auto_promotion": False,
        "workstation_lane_authority_preserved": True,
    },
}

queue_doc = {
    "schema": "vertex-vxs/ir-maturation-queue-4",
    "mapping_ready_count": len(mapping_ready),
    "mapping_candidate_count": len(mapping_candidate),
    "research_required_count": len(research_required),
    "items": ir_queue,
    "rule": "IR mapping precedes native promotion; no discovery seed self-promotes",
}

wave_doc = {
    "schema": "vertex-vxs/native-promotion-wave-4",
    "ready_native_count": len(ready),
    "wave_size": wave_size,
    "wave_count": len(waves),
    "waves": waves,
    "next_candidate": ready[0] if ready else None,
    "authority": "HUMAN_APPLY",
    "lane_allocation_authority": "VERTEX_WORKSTATION",
}

sat_doc = {
    "schema": "vertex-vxs/native-saturation-report-4",
    "census_command_count": len(census_commands),
    "seed_bank_command_count": len(seed_bank_commands),
    "unbanked_command_count_before_recensus": len(unbanked_commands),
    "existing_native_resource_count": len(already_native),
    "ready_native_count": len(ready),
    "discovery_only_count": len(discovery),
    "ir_mapping_ready_count": len(mapping_ready),
    "ir_mapping_candidate_count": len(mapping_candidate),
    "research_required_count": len(research_required),
    "known_surface_units": known_surface,
    "resolved_surface_units": resolved_surface,
    "engineering_saturation_ratio": round(saturation_ratio, 6),
    "interpretation": "bounded to discovered/censused surface; not proof of total PowerShell completeness",
    "hard_stop_conditions": [
        "no READY_NATIVE and no IR_MAPPING_READY",
        "all remaining seeds require research or mutation authority",
        "source census/IR/graph changes invalidate this snapshot",
    ],
}

for path, doc in (
    (FARM_V4, farm_doc),
    (IR_QUEUE_V4, queue_doc),
    (WAVE_V4, wave_doc),
    (SAT_V4, sat_doc),
):
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

# Durable self-checks.
checks = [
    (FARM_V4, "vertex-vxs/native-capability-farm-4"),
    (IR_QUEUE_V4, "vertex-vxs/ir-maturation-queue-4"),
    (WAVE_V4, "vertex-vxs/native-promotion-wave-4"),
    (SAT_V4, "vertex-vxs/native-saturation-report-4"),
]
for path, schema in checks:
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("schema") != schema:
        raise SystemExit(fail("PERSISTED_SCHEMA", 40, f"{path.name}:{d.get('schema')}"))

if farm_doc["policy"]["human_gate_preserved"] is not True:
    raise SystemExit(fail("HUMAN_GATE_GUARD", 41))
if farm_doc["policy"]["powershell_backend_preserved"] is not True:
    raise SystemExit(fail("BACKEND_GUARD", 42))
if farm_doc["policy"]["mutation_native_auto_promotion"] is not False:
    raise SystemExit(fail("MUTATION_GUARD", 43))
if farm_doc["policy"]["discovery_only_native_auto_promotion"] is not False:
    raise SystemExit(fail("DISCOVERY_GUARD", 44))

if not ready and not mapping_ready and not mapping_candidate and not research_required:
    raise SystemExit(fail("SATURATION_SURFACE_EMPTY", 45))

print("VXS_NATIVE_FARM_SATURATION=PASS")
print("CENSUS_COMMAND_COUNT=" + str(len(census_commands)))
print("EXISTING_NATIVE_RESOURCE_COUNT=" + str(len(already_native)))
print("READY_NATIVE_COUNT=" + str(len(ready)))
print("DISCOVERY_ONLY_COUNT=" + str(len(discovery)))
print("IR_MAPPING_READY_COUNT=" + str(len(mapping_ready)))
print("IR_MAPPING_CANDIDATE_COUNT=" + str(len(mapping_candidate)))
print("RESEARCH_REQUIRED_COUNT=" + str(len(research_required)))
print("PROMOTION_WAVE_COUNT=" + str(len(waves)))
print("ENGINEERING_SATURATION_RATIO=" + str(round(saturation_ratio, 6)))

if ready:
    print("NEXT_NATIVE_RESOURCE=" + ready[0]["resource"])
    print("NEXT_NATIVE_DECISION=" + str(ready[0].get("decision")))
    print("NEXT_NATIVE_SCORE=" + str(ready[0].get("score")))
else:
    print("NEXT_NATIVE_RESOURCE=NONE")

if mapping_ready:
    print("NEXT_IR_SEED=" + mapping_ready[0]["resource_seed"])
    print("NEXT_IR_SEED_SCORE=" + str(mapping_ready[0]["score"]))
elif mapping_candidate:
    print("NEXT_IR_SEED=" + mapping_candidate[0]["resource_seed"])
    print("NEXT_IR_SEED_SCORE=" + str(mapping_candidate[0]["score"]))
else:
    print("NEXT_IR_SEED=NONE")

print("FARM_V4_PATH=" + str(FARM_V4))
print("FARM_V4_SHA256=" + sha256_file(FARM_V4))
print("IR_QUEUE_V4_PATH=" + str(IR_QUEUE_V4))
print("IR_QUEUE_V4_SHA256=" + sha256_file(IR_QUEUE_V4))
print("WAVE_V4_PATH=" + str(WAVE_V4))
print("WAVE_V4_SHA256=" + sha256_file(WAVE_V4))
print("SATURATION_V4_PATH=" + str(SAT_V4))
print("SATURATION_V4_SHA256=" + sha256_file(SAT_V4))
print("HUMAN_GATE_PRESERVED=true")
print("POWERSHELL_BACKEND_PRESERVED=true")
print("WORKSTATION_LANE_AUTHORITY_PRESERVED=true")
print("DISCOVERY_ONLY_AUTO_PROMOTION=false")
print("MUTATION_NATIVE_AUTO_PROMOTION=false")
raise SystemExit(0)
