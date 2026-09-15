from __future__ import annotations

from pathlib import Path
import json
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "runtime" / "vxs" / "predation" / "powershell-7.6.6-native-promotion-plan.json"
PLAN_SCHEMA = "vertex-vxs/native-promotion-plan-1"

ALREADY_NATIVE = {"SYSTEM", "FILESYSTEM"}

def fail(stage: str, code: int, extra: str = "") -> int:
    print("VXS_REATTACK_RAY=FAIL")
    print("STAGE=" + stage)
    if extra:
        print(extra)
    return code

if not PLAN.is_file():
    raise SystemExit(fail("PLAN_LOOKUP", 20, "EXPECTED=" + str(PLAN)))

try:
    plan = json.loads(PLAN.read_text(encoding="utf-8-sig"))
except Exception as exc:
    raise SystemExit(fail("PLAN_PARSE", 21, f"ERROR={type(exc).__name__}:{exc}"))

if plan.get("schema") != PLAN_SCHEMA:
    raise SystemExit(fail("PLAN_SCHEMA", 22, "FOUND=" + str(plan.get("schema"))))

organs = plan.get("native_organs")
if not isinstance(organs, list):
    raise SystemExit(fail("NATIVE_ORGANS_TYPE", 23))

rows = []
resource_counts = Counter()
decision_counts = Counter()
resource_scores = defaultdict(list)

for index, organ in enumerate(organs):
    if not isinstance(organ, dict):
        continue

    resource = str(organ.get("resource") or "UNKNOWN").upper()
    decision = str(
        organ.get("decision")
        or organ.get("promotion_decision")
        or organ.get("status")
        or "UNKNOWN"
    ).upper()

    score_raw = (
        organ.get("score")
        if organ.get("score") is not None
        else organ.get("promotion_score")
    )
    try:
        score = float(score_raw) if score_raw is not None else None
    except Exception:
        score = None

    actions = organ.get("actions")
    if not isinstance(actions, list):
        action = organ.get("action")
        actions = [str(action)] if action else []

    authority = str(
        organ.get("authority")
        or organ.get("authority_candidate")
        or "UNKNOWN"
    ).upper()

    side_effect = str(
        organ.get("side_effect")
        or organ.get("side_effect_class")
        or "UNKNOWN"
    ).upper()

    row = {
        "index": index,
        "resource": resource,
        "decision": decision,
        "score": score,
        "actions": actions,
        "authority": authority,
        "side_effect": side_effect,
        "raw": organ,
    }
    rows.append(row)
    resource_counts[resource] += 1
    decision_counts[decision] += 1
    if score is not None:
        resource_scores[resource].append(score)

eligible = [
    row for row in rows
    if row["resource"] not in ALREADY_NATIVE
    and row["resource"] != "UNKNOWN"
]

priority = {
    "PROMOTE_NOW": 0,
    "PROMOTE_NEXT": 1,
    "KEEP_HYBRID": 2,
    "POWERSHELL_BACKEND": 3,
    "UNKNOWN": 9,
}

eligible.sort(
    key=lambda row: (
        priority.get(row["decision"], 8),
        -(row["score"] if row["score"] is not None else -1.0),
        row["resource"],
        row["index"],
    )
)

selected = eligible[0] if eligible else None

report = {
    "schema": "vertex-vxs/native-organ-reattack-ray-1",
    "state": "PASS",
    "plan": str(PLAN),
    "native_organ_count": len(rows),
    "resource_counts": dict(sorted(resource_counts.items())),
    "decision_counts": dict(sorted(decision_counts.items())),
    "already_native": sorted(ALREADY_NATIVE),
    "eligible_count": len(eligible),
    "eligible": [
        {
            "index": row["index"],
            "resource": row["resource"],
            "decision": row["decision"],
            "score": row["score"],
            "actions": row["actions"],
            "authority": row["authority"],
            "side_effect": row["side_effect"],
        }
        for row in eligible[:64]
    ],
    "selected": None if selected is None else {
        "index": selected["index"],
        "resource": selected["resource"],
        "decision": selected["decision"],
        "score": selected["score"],
        "actions": selected["actions"],
        "authority": selected["authority"],
        "side_effect": selected["side_effect"],
    },
}

print("VXS_REATTACK_RAY=PASS")
print("PLAN_SCHEMA=" + str(plan.get("schema")))
print("NATIVE_ORGAN_COUNT=" + str(len(rows)))
print("ELIGIBLE_COUNT=" + str(len(eligible)))
print("RESOURCES=" + ",".join(sorted(resource_counts.keys())))
print("DECISIONS=" + ",".join(f"{k}:{v}" for k, v in sorted(decision_counts.items())))

if selected is None:
    print("SELECTED_RESOURCE=NONE")
    print("SELECTED_DECISION=NONE")
    print("SELECTED_SCORE=NONE")
else:
    print("SELECTED_RESOURCE=" + selected["resource"])
    print("SELECTED_DECISION=" + selected["decision"])
    print("SELECTED_SCORE=" + ("NONE" if selected["score"] is None else str(selected["score"])))
    print("SELECTED_ACTIONS=" + ",".join(str(x) for x in selected["actions"]))
    print("SELECTED_AUTHORITY=" + selected["authority"])
    print("SELECTED_SIDE_EFFECT=" + selected["side_effect"])

print("VXS_REATTACK_REPORT=" + json.dumps(report, ensure_ascii=False, separators=(",", ":")))

if selected is None:
    raise SystemExit(25)

raise SystemExit(0)
