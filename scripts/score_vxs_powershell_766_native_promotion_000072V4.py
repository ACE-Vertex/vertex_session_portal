from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import math
import sys
from typing import Any

EXPECTED_PS_VERSION = "7.6.6"
IR_SCHEMA = "vertex-vxs/powershell-capability-ir-ingestion-1"
GRAPH_SCHEMA_PREFIX = "vertex-vxs/capability-graph-"
PROMOTION_SCHEMA = "vertex-vxs/native-promotion-plan-1"

# First organ targets: capabilities that are safe, common, and naturally expressible
# in a native Windows/Rust provider without inheriting PowerShell semantics.
RESOURCE_NATIVE_EASE = {
    "PROCESS": 1.00,
    "SERVICE": 0.92,
    "FILESYSTEM": 0.95,
    "NETWORK": 0.88,
    "SYSTEM": 0.85,
    "EVENTLOG": 0.72,
    "REGISTRY": 0.70,
    "JOB": 0.70,
    "SHELL": 0.45,
    "SECURITY": 0.40,
    "PACKAGE": 0.38,
    "PRINTER": 0.50,
    "UNKNOWN": 0.15,
}

ACTION_NATIVE_EASE = {
    "OBSERVE": 1.00,
    "TEST": 0.96,
    "FIND": 0.92,
    "MEASURE": 0.90,
    "COMPARE": 0.82,
    "RESOLVE": 0.82,
    "START": 0.65,
    "STOP": 0.58,
    "RESTART": 0.52,
    "ENABLE": 0.56,
    "DISABLE": 0.56,
    "CREATE": 0.48,
    "UPDATE": 0.45,
    "ADD": 0.45,
    "REMOVE": 0.30,
    "COPY": 0.52,
    "MOVE": 0.45,
    "RENAME": 0.45,
    "IMPORT": 0.30,
    "EXPORT": 0.42,
    "WRITE": 0.38,
    "INSTALL": 0.25,
    "INVOKE": 0.15,
    "UNKNOWN": 0.10,
}

SIDE_EFFECT_SAFETY = {
    "NONE": 1.00,
    "MUTATING": 0.45,
    "DISRUPTIVE": 0.25,
    "DESTRUCTIVE": 0.10,
    "UNKNOWN_MUTATION": 0.05,
}

AUTHORITY_WEIGHT = {
    "AUTO_SAFE": 1.00,
    "HUMAN_APPLY": 0.40,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def normalize_frequency(count: int, maximum: int) -> float:
    if maximum <= 0 or count <= 0:
        return 0.0
    return math.log1p(count) / math.log1p(maximum)


def bucket(score: float) -> str:
    if score >= 0.82:
        return "PROMOTE_NOW"
    if score >= 0.68:
        return "PROMOTE_NEXT"
    if score >= 0.52:
        return "KEEP_HYBRID"
    return "POWERSHELL_BACKEND"


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    predation_dir = root / "runtime" / "vxs" / "predation"

    ir_path = predation_dir / f"powershell-{EXPECTED_PS_VERSION}-capability-ir.json"
    graph_path = predation_dir / f"powershell-{EXPECTED_PS_VERSION}-capability-graph.json"

    if not ir_path.is_file():
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=IR_LOOKUP")
        print("EXPECTED=" + str(ir_path))
        return 20

    if not graph_path.is_file():
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=GRAPH_LOOKUP")
        print("EXPECTED=" + str(graph_path))
        return 21

    try:
        ir_doc = json.loads(ir_path.read_text(encoding="utf-8-sig"))
        graph_doc = json.loads(graph_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=INPUT_PARSE")
        print("ERROR=" + type(exc).__name__ + ":" + str(exc))
        return 22

    if ir_doc.get("schema") != IR_SCHEMA:
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=IR_SCHEMA")
        print("FOUND=" + str(ir_doc.get("schema")))
        return 23

    graph_schema = str(graph_doc.get("schema") or "")
    if not graph_schema.startswith(GRAPH_SCHEMA_PREFIX):
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=GRAPH_SCHEMA")
        print("FOUND=" + graph_schema)
        return 24

    runtime_version = str((ir_doc.get("generated_from") or {}).get("runtime_version") or "")
    if runtime_version != EXPECTED_PS_VERSION:
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=RUNTIME_VERSION")
        print("FOUND=" + runtime_version)
        return 25

    capabilities = ir_doc.get("capabilities") or []
    if not isinstance(capabilities, list) or not capabilities:
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=IR_EMPTY")
        return 26

    # Frequency from the graph's ACTION-RESOURCE synapses.
    pair_frequency: Counter[tuple[str, str]] = Counter()
    for edge in graph_doc.get("edges") or []:
        if edge.get("kind") != "ACTION_RESOURCE_COOCCURRENCE":
            continue
        src = str(edge.get("from") or "")
        dst = str(edge.get("to") or "")
        if not src.startswith("action:") or not dst.startswith("resource:"):
            continue
        action = src.split(":", 1)[1].replace("-", "_").upper()
        resource = dst.split(":", 1)[1].replace("-", "_").upper()
        pair_frequency[(action, resource)] += int(edge.get("weight") or 0)

    # Prefer direct recomputation as canonical data; graph frequency is advisory.
    direct_pair_frequency: Counter[tuple[str, str]] = Counter(
        (str(c.get("action") or "UNKNOWN"), str(c.get("resource") or "UNKNOWN"))
        for c in capabilities
    )
    max_freq = max(direct_pair_frequency.values()) if direct_pair_frequency else 1

    candidates: list[dict[str, Any]] = []

    for cap in capabilities:
        cap_id = str(cap.get("capability_id") or "")
        action = str(cap.get("action") or "UNKNOWN")
        resource = str(cap.get("resource") or "UNKNOWN")
        authority = str(cap.get("authority") or "HUMAN_APPLY")
        side_effect = str(cap.get("side_effect") or "UNKNOWN_MUTATION")

        freq_count = int(direct_pair_frequency[(action, resource)])
        freq_score = normalize_frequency(freq_count, max_freq)
        safety_score = SIDE_EFFECT_SAFETY.get(side_effect, 0.05)
        authority_score = AUTHORITY_WEIGHT.get(authority, 0.30)
        resource_ease = RESOURCE_NATIVE_EASE.get(resource, 0.45)
        action_ease = ACTION_NATIVE_EASE.get(action, 0.40)
        native_ease = (resource_ease * 0.55) + (action_ease * 0.45)

        # PowerShell-dependence penalty:
        # lots of parameters and SHELL-like semantics tend to carry PS-specific behavior.
        param_count = len(cap.get("parameters") or [])
        parameter_complexity = clamp(param_count / 40.0)
        shell_penalty = 0.35 if resource == "SHELL" else 0.0
        invoke_penalty = 0.35 if action == "INVOKE" else 0.0
        dependency_penalty = clamp(
            parameter_complexity * 0.35 + shell_penalty + invoke_penalty
        )

        # Promotion score weights:
        # safety and native expressibility dominate.
        score = (
            freq_score * 0.20
            + safety_score * 0.25
            + authority_score * 0.15
            + native_ease * 0.30
            + (1.0 - dependency_penalty) * 0.10
        )
        score = round(clamp(score), 6)

        source_info = cap.get("source") or {}
        candidates.append({
            "capability_id": cap_id,
            "action": action,
            "resource": resource,
            "authority": authority,
            "side_effect": side_effect,
            "score": score,
            "decision": bucket(score),
            "metrics": {
                "frequency_count": freq_count,
                "frequency_score": round(freq_score, 6),
                "safety_score": round(safety_score, 6),
                "authority_score": round(authority_score, 6),
                "native_ease": round(native_ease, 6),
                "dependency_penalty": round(dependency_penalty, 6),
                "parameter_count": param_count,
            },
            "source": {
                "command_name": source_info.get("command_name"),
                "module_name": source_info.get("module_name"),
                "runtime_version": source_info.get("runtime_version"),
            },
        })

    # Deduplicate semantic capability IDs, keeping the highest score as representative.
    best_by_capability: dict[str, dict[str, Any]] = {}
    for item in candidates:
        cap_id = item["capability_id"]
        current = best_by_capability.get(cap_id)
        if current is None or item["score"] > current["score"]:
            best_by_capability[cap_id] = item

    ranked = sorted(
        best_by_capability.values(),
        key=lambda x: (-x["score"], x["resource"], x["action"], x["capability_id"]),
    )

    decision_counts = Counter(x["decision"] for x in ranked)

    # Organ candidates are deliberately bounded and read-first.
    organ_candidates = [
        x for x in ranked
        if x["decision"] == "PROMOTE_NOW"
        and x["authority"] == "AUTO_SAFE"
        and x["side_effect"] == "NONE"
    ][:64]

    # Group first-wave organ candidates by resource to define provider boundaries.
    provider_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in organ_candidates:
        provider_groups[item["resource"]].append(item)

    native_organs = []
    for resource, items in sorted(
        provider_groups.items(),
        key=lambda kv: (-len(kv[1]), kv[0]),
    ):
        native_organs.append({
            "organ_id": "vxs-native-" + resource.lower().replace("_", "-"),
            "resource": resource,
            "provider_language": "rust",
            "transport": "vxn",
            "authority_default": "AUTO_SAFE",
            "capability_count": len(items),
            "capabilities": [
                {
                    "capability_id": x["capability_id"],
                    "action": x["action"],
                    "score": x["score"],
                    "source_command": x["source"]["command_name"],
                }
                for x in items
            ],
        })

    plan = {
        "schema": PROMOTION_SCHEMA,
        "runtime_version": runtime_version,
        "generated_from": {
            "ir_path": str(ir_path),
            "ir_sha256": sha256_file(ir_path),
            "graph_path": str(graph_path),
            "graph_sha256": sha256_file(graph_path),
        },
        "policy": {
            "promotion_thresholds": {
                "PROMOTE_NOW": 0.82,
                "PROMOTE_NEXT": 0.68,
                "KEEP_HYBRID": 0.52,
            },
            "first_wave_rule": "AUTO_SAFE + NONE side effect + PROMOTE_NOW",
            "native_language": "rust",
            "transport": "vxn",
            "powershell_role_after_promotion": "teacher-and-fallback",
        },
        "summary": {
            "input_ir_record_count": len(capabilities),
            "semantic_capability_count": len(ranked),
            "promotion_decision_counts": dict(sorted(decision_counts.items())),
            "first_wave_organ_candidate_count": len(organ_candidates),
            "native_organ_count": len(native_organs),
        },
        "native_organs": native_organs,
        "top_candidates": ranked[:200],
    }

    out_path = predation_dir / f"powershell-{EXPECTED_PS_VERSION}-native-promotion-plan.json"
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

    predation_dir.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    persisted = json.loads(tmp_path.read_text(encoding="utf-8"))
    if persisted.get("schema") != PROMOTION_SCHEMA:
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=PERSISTED_SCHEMA")
        return 30

    summary = persisted.get("summary") or {}
    if int(summary.get("semantic_capability_count") or 0) != len(ranked):
        print("VXS_NATIVE_PROMOTION=FAIL")
        print("STAGE=SEMANTIC_COUNT")
        return 31

    # Atomic promotion after validation.
    tmp_path.replace(out_path)

    out_sha = sha256_file(out_path)
    out_bytes = out_path.stat().st_size

    print("VXS_NATIVE_PROMOTION=PASS")
    print("PS_VERSION=" + runtime_version)
    print("IR_RECORD_COUNT=" + str(len(capabilities)))
    print("SEMANTIC_CAPABILITY_COUNT=" + str(len(ranked)))
    print("PROMOTE_NOW_COUNT=" + str(decision_counts.get("PROMOTE_NOW", 0)))
    print("PROMOTE_NEXT_COUNT=" + str(decision_counts.get("PROMOTE_NEXT", 0)))
    print("KEEP_HYBRID_COUNT=" + str(decision_counts.get("KEEP_HYBRID", 0)))
    print("POWERSHELL_BACKEND_COUNT=" + str(decision_counts.get("POWERSHELL_BACKEND", 0)))
    print("FIRST_WAVE_ORGAN_CANDIDATE_COUNT=" + str(len(organ_candidates)))
    print("NATIVE_ORGAN_COUNT=" + str(len(native_organs)))
    print("PLAN_PATH=" + str(out_path))
    print("PLAN_BYTES=" + str(out_bytes))
    print("PLAN_SHA256=" + out_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
