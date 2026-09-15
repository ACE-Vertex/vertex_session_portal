from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import os
import re
import sys
from typing import Any

IR_DOCUMENT_SCHEMA = "vertex-vxs/powershell-capability-ir-ingestion-1"
IR_RECORD_SCHEMA = "vxs-capability-ir/1"
GRAPH_SCHEMA = "vertex-vxs/capability-graph-2"
EXPECTED_PS_VERSION = "7.6.6"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_id(prefix: str, value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return f"{prefix}:{safe or 'unknown'}"


def short_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    predation_dir = root / "runtime" / "vxs" / "predation"
    ir_path = predation_dir / f"powershell-{EXPECTED_PS_VERSION}-capability-ir.json"

    if not ir_path.is_file():
        print("VXS_GRAPH=FAIL")
        print("STAGE=IR_LOOKUP")
        print("EXPECTED=" + str(ir_path))
        return 20

    ir_sha = sha256_file(ir_path)

    try:
        ir_doc = json.loads(ir_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print("VXS_GRAPH=FAIL")
        print("STAGE=IR_PARSE")
        print("ERROR=" + type(exc).__name__ + ":" + str(exc))
        return 21

    if ir_doc.get("schema") != IR_DOCUMENT_SCHEMA:
        print("VXS_GRAPH=FAIL")
        print("STAGE=IR_DOCUMENT_SCHEMA")
        print("FOUND=" + str(ir_doc.get("schema")))
        return 22

    generated_from = ir_doc.get("generated_from") or {}
    runtime_version = str(generated_from.get("runtime_version") or "")
    if runtime_version != EXPECTED_PS_VERSION:
        print("VXS_GRAPH=FAIL")
        print("STAGE=RUNTIME_VERSION")
        print("FOUND=" + runtime_version)
        return 23

    capabilities = ir_doc.get("capabilities") or []
    if not isinstance(capabilities, list) or not capabilities:
        print("VXS_GRAPH=FAIL")
        print("STAGE=IR_EMPTY")
        return 24

    for idx, cap in enumerate(capabilities):
        if cap.get("schema") != IR_RECORD_SCHEMA:
            print("VXS_GRAPH=FAIL")
            print("STAGE=IR_RECORD_SCHEMA")
            print("INDEX=" + str(idx))
            return 25
        if not str(cap.get("capability_id") or "").strip():
            print("VXS_GRAPH=FAIL")
            print("STAGE=CAPABILITY_ID")
            print("INDEX=" + str(idx))
            return 26

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_ids: set[str] = set()

    def add_node(node: dict[str, Any]) -> None:
        node_id = str(node["id"])
        if node_id in node_ids:
            return
        node_ids.add(node_id)
        nodes.append(node)

    action_counts: Counter[str] = Counter()
    resource_counts: Counter[str] = Counter()
    authority_counts: Counter[str] = Counter()
    side_effect_counts: Counter[str] = Counter()
    semantic_counts: Counter[str] = Counter()
    action_resource_counts: Counter[tuple[str, str]] = Counter()
    action_resource_caps: dict[tuple[str, str], list[str]] = defaultdict(list)

    # Census the semantic dimensions.
    for cap in capabilities:
        action = str(cap.get("action") or "UNKNOWN")
        resource = str(cap.get("resource") or "UNKNOWN")
        authority = str(cap.get("authority") or "HUMAN_APPLY")
        side_effect = str(cap.get("side_effect") or "UNKNOWN_MUTATION")
        cap_id = str(cap.get("capability_id") or "")

        action_counts[action] += 1
        resource_counts[resource] += 1
        authority_counts[authority] += 1
        side_effect_counts[side_effect] += 1
        semantic_counts[cap_id] += 1

        pair = (action, resource)
        action_resource_counts[pair] += 1
        if len(action_resource_caps[pair]) < 12:
            action_resource_caps[pair].append(cap_id)

    # Hubs.
    for action, count in sorted(action_counts.items()):
        add_node({"id": stable_id("action", action), "kind": "ACTION", "label": action, "weight": count})

    for resource, count in sorted(resource_counts.items()):
        add_node({"id": stable_id("resource", resource), "kind": "RESOURCE", "label": resource, "weight": count})

    for authority, count in sorted(authority_counts.items()):
        add_node({"id": stable_id("authority", authority), "kind": "AUTHORITY", "label": authority, "weight": count})

    for side_effect, count in sorted(side_effect_counts.items()):
        add_node({"id": stable_id("side-effect", side_effect), "kind": "SIDE_EFFECT", "label": side_effect, "weight": count})

    # Semantic Capability nodes: one per unique capability_id.
    for cap_id, count in sorted(semantic_counts.items()):
        add_node({
            "id": "capability:" + cap_id,
            "kind": "CAPABILITY",
            "label": cap_id,
            "instance_count": count,
            "is_duplicated": count > 1,
        })

    # Capability Instance nodes: one per IR record.
    # Duplicates are not discarded; each source record gets a distinct instance node.
    for idx, cap in enumerate(capabilities):
        cap_id = str(cap["capability_id"])
        action = str(cap.get("action") or "UNKNOWN")
        resource = str(cap.get("resource") or "UNKNOWN")
        authority = str(cap.get("authority") or "HUMAN_APPLY")
        side_effect = str(cap.get("side_effect") or "UNKNOWN_MUTATION")

        source_descriptor = {
            "index": idx,
            "capability_id": cap_id,
            "source": cap.get("source"),
            "target": cap.get("target"),
            "parameters": cap.get("parameters") or [],
        }
        instance_id = f"capability-instance:{idx:06d}:{short_digest(source_descriptor)}"

        add_node({
            "id": instance_id,
            "kind": "CAPABILITY_INSTANCE",
            "label": cap_id,
            "record_index": idx,
            "capability_id": cap_id,
            "provider": cap.get("provider"),
            "source": cap.get("source"),
            "target": cap.get("target"),
            "parameters": cap.get("parameters") or [],
        })

        edges.extend([
            {"from": instance_id, "to": "capability:" + cap_id, "kind": "INSTANCE_OF", "weight": 1},
            {"from": instance_id, "to": stable_id("action", action), "kind": "HAS_ACTION", "weight": 1},
            {"from": instance_id, "to": stable_id("resource", resource), "kind": "TARGETS_RESOURCE", "weight": 1},
            {"from": instance_id, "to": stable_id("authority", authority), "kind": "REQUIRES_AUTHORITY", "weight": 1},
            {"from": instance_id, "to": stable_id("side-effect", side_effect), "kind": "HAS_SIDE_EFFECT", "weight": 1},
        ])

    # Weighted semantic synapses: ACTION -> RESOURCE co-occurrence.
    for (action, resource), count in sorted(
        action_resource_counts.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    ):
        edges.append({
            "from": stable_id("action", action),
            "to": stable_id("resource", resource),
            "kind": "ACTION_RESOURCE_COOCCURRENCE",
            "weight": count,
            "sample_capabilities": action_resource_caps[(action, resource)],
        })

    # Full integrity validation before any durable output write.
    edge_kinds = Counter(str(e["kind"]) for e in edges)
    dangling = [
        e for e in edges
        if str(e["from"]) not in node_ids or str(e["to"]) not in node_ids
    ]
    if dangling:
        print("VXS_GRAPH=FAIL")
        print("STAGE=DANGLING_EDGE_PREWRITE")
        print("COUNT=" + str(len(dangling)))
        return 30

    instance_count = sum(1 for n in nodes if n.get("kind") == "CAPABILITY_INSTANCE")
    semantic_count = sum(1 for n in nodes if n.get("kind") == "CAPABILITY")

    if instance_count != len(capabilities):
        print("VXS_GRAPH=FAIL")
        print("STAGE=CAPABILITY_INSTANCE_COUNT")
        print("EXPECTED=" + str(len(capabilities)))
        print("FOUND=" + str(instance_count))
        return 33

    if semantic_count != len(semantic_counts):
        print("VXS_GRAPH=FAIL")
        print("STAGE=SEMANTIC_CAPABILITY_COUNT")
        print("EXPECTED=" + str(len(semantic_counts)))
        print("FOUND=" + str(semantic_count))
        return 34

    duplicate_ids = sorted(cap_id for cap_id, count in semantic_counts.items() if count > 1)

    document = {
        "schema": GRAPH_SCHEMA,
        "generated_at_utc": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "source": {
            "path": str(ir_path),
            "sha256": ir_sha,
            "schema": ir_doc.get("schema"),
            "runtime_version": runtime_version,
        },
        "summary": {
            "capability_record_count": len(capabilities),
            "semantic_capability_count": len(semantic_counts),
            "duplicate_capability_id_count": len(duplicate_ids),
            "capability_instance_node_count": instance_count,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "action_hub_count": len(action_counts),
            "resource_hub_count": len(resource_counts),
            "authority_hub_count": len(authority_counts),
            "side_effect_hub_count": len(side_effect_counts),
            "action_resource_synapse_count": len(action_resource_counts),
            "edge_kind_counts": dict(sorted(edge_kinds.items())),
            "top_action_resource_synapses": [
                {"action": action, "resource": resource, "weight": count}
                for (action, resource), count in action_resource_counts.most_common(25)
            ],
        },
        "duplicate_capability_ids": duplicate_ids[:200],
        "nodes": nodes,
        "edges": edges,
    }

    graph_path = predation_dir / f"powershell-{EXPECTED_PS_VERSION}-capability-graph.json"
    tmp_path = graph_path.with_suffix(graph_path.suffix + ".tmp")

    predation_dir.mkdir(parents=True, exist_ok=True)
    try:
        tmp_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

        # Re-read the temporary durable file before promotion.
        persisted = json.loads(tmp_path.read_text(encoding="utf-8"))
        if persisted.get("schema") != GRAPH_SCHEMA:
            print("VXS_GRAPH=FAIL")
            print("STAGE=TEMP_SCHEMA")
            return 31

        persisted_nodes = persisted.get("nodes") or []
        persisted_edges = persisted.get("edges") or []
        persisted_ids = {str(n.get("id")) for n in persisted_nodes}

        dangling_after = [
            e for e in persisted_edges
            if str(e.get("from")) not in persisted_ids or str(e.get("to")) not in persisted_ids
        ]
        if dangling_after:
            print("VXS_GRAPH=FAIL")
            print("STAGE=TEMP_DANGLING_EDGE")
            print("COUNT=" + str(len(dangling_after)))
            return 32

        persisted_instances = sum(
            1 for n in persisted_nodes if n.get("kind") == "CAPABILITY_INSTANCE"
        )
        persisted_semantics = sum(
            1 for n in persisted_nodes if n.get("kind") == "CAPABILITY"
        )
        if persisted_instances != len(capabilities):
            print("VXS_GRAPH=FAIL")
            print("STAGE=TEMP_INSTANCE_COUNT")
            return 35
        if persisted_semantics != len(semantic_counts):
            print("VXS_GRAPH=FAIL")
            print("STAGE=TEMP_SEMANTIC_COUNT")
            return 36

        # Atomic promotion only after all checks pass.
        os.replace(tmp_path, graph_path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    graph_sha = sha256_file(graph_path)
    graph_bytes = graph_path.stat().st_size

    print("VXS_GRAPH=PASS")
    print("PS_VERSION=" + runtime_version)
    print("IR_SHA256=" + ir_sha)
    print("CAPABILITY_RECORD_COUNT=" + str(len(capabilities)))
    print("SEMANTIC_CAPABILITY_COUNT=" + str(len(semantic_counts)))
    print("DUPLICATE_CAPABILITY_ID_COUNT=" + str(len(duplicate_ids)))
    print("CAPABILITY_INSTANCE_NODE_COUNT=" + str(instance_count))
    print("NODE_COUNT=" + str(len(nodes)))
    print("EDGE_COUNT=" + str(len(edges)))
    print("ACTION_HUB_COUNT=" + str(len(action_counts)))
    print("RESOURCE_HUB_COUNT=" + str(len(resource_counts)))
    print("ACTION_RESOURCE_SYNAPSE_COUNT=" + str(len(action_resource_counts)))
    print("GRAPH_PATH=" + str(graph_path))
    print("GRAPH_BYTES=" + str(graph_bytes))
    print("GRAPH_SHA256=" + graph_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
