from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "runtime" / "vxs" / "predation" / "powershell-7.6.6-native-promotion-plan.json"
PLAN_SCHEMA = "vertex-vxs/native-promotion-plan-1"
ALREADY_NATIVE = {"SYSTEM", "FILESYSTEM"}

PRIORITY = {
    "PROMOTE_NOW": 0,
    "PROMOTE_NEXT": 1,
    "KEEP_HYBRID": 2,
    "POWERSHELL_BACKEND": 3,
    "UNKNOWN": 9,
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fail(stage: str, code: int, extra: str = "") -> int:
    print("VXS_SECOND_ORGAN_GENESIS=FAIL")
    print("STAGE=" + stage)
    if extra:
        print(extra)
    return code

def run(args: list[str], cwd: Path, timeout: int = 120):
    return subprocess.run(
        args,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=timeout,
    )

if not PLAN.is_file():
    raise SystemExit(fail("PLAN_LOOKUP", 20, "EXPECTED=" + str(PLAN)))

try:
    plan = json.loads(PLAN.read_text(encoding="utf-8-sig"))
except Exception as exc:
    raise SystemExit(fail("PLAN_PARSE", 21, f"ERROR={type(exc).__name__}:{exc}"))

if plan.get('schema') != PLAN_SCHEMA:
    raise SystemExit(fail("PLAN_SCHEMA", 22, "FOUND=" + str(plan.get("schema"))))

organs = plan.get("native_organs")
if not isinstance(organs, list):
    raise SystemExit(fail("NATIVE_ORGANS_TYPE", 23))

rows = []
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
    score_raw = organ.get("score")
    if score_raw is None:
        score_raw = organ.get("promotion_score")
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
    rows.append({
        "index": index,
        "resource": resource,
        "decision": decision,
        "score": score,
        "actions": [str(a) for a in actions],
        "authority": authority,
        "side_effect": side_effect,
    })

eligible = [
    row for row in rows
    if row["resource"] not in ALREADY_NATIVE
    and row["resource"] != "UNKNOWN"
]

eligible.sort(
    key=lambda row: (
        PRIORITY.get(row["decision"], 8),
        -(row["score"] if row["score"] is not None else -1.0),
        row["resource"],
        row["index"],
    )
)

if not eligible:
    raise SystemExit(fail("SELECTION", 25, "SELECTED_RESOURCE=NONE"))

selected = eligible[0]
resource = selected["resource"]
slug = resource.lower().replace("_", "-")
organ_id = f"vxs-native-{slug}-observer"

rust_lines = [
    "use std::env;",
    "",
    "fn main() {",
    '    let cmd = env::args().nth(1).unwrap_or_else(|| "identity".to_string());',
    "",
    "    match cmd.as_str() {",
    '        "identity" => {',
    '            println!(r#"{{"schema":"vertex-vxs/native-organ-output-1","organ":"second-organ","organ_id":"__ORGAN_ID__","resource":"__RESOURCE__","status":"SCAFFOLDED_TEST"}}"#);',
    "        }",
    '        "selftest" => {',
    '            println!(r#"{{"schema":"vertex-vxs/native-organ-output-1","organ":"second-organ","organ_id":"__ORGAN_ID__","resource":"__RESOURCE__","selftest":true}}"#);',
    "        }",
    "        _ => {",
    '            eprintln!("unsupported genesis command");',
    "            std::process::exit(2);",
    "        }",
    "    }",
    "}",
]
rust_source = "\n".join(rust_lines).replace("__ORGAN_ID__", organ_id).replace("__RESOURCE__", resource) + "\n"

selection_dir = ROOT / "runtime" / "vxs" / "predation" / "second-organ"
organ_root = ROOT / "runtime" / "vxs" / "predation" / "native-organs" / organ_id
src_dir = organ_root / "src"
selection_path = selection_dir / "selection-000081V4.json"
rs_path = src_dir / "main.rs"
manifest_path = organ_root / "organ.json"

selection = {
    "schema": "vertex-vxs/second-organ-selection-1",
    "source_plan": str(PLAN),
    "source_plan_sha256": sha256_file(PLAN),
    "algorithm": "same-as-reattack-ray-000080V4",
    "already_native": sorted(ALREADY_NATIVE),
    "eligible_count": len(eligible),
    "selected": {
        "index": selected["index"],
        "resource": resource,
        "decision": selected["decision"],
        "score": selected["score"],
        "actions": selected["actions"],
        "authority": selected["authority"],
        "side_effect": selected["side_effect"],
    },
}

manifest = {
    "schema": "vertex-vxs/native-organ-1",
    "organ_id": organ_id,
    "ordinal": 2,
    "resource": resource,
    "status": "SCAFFOLDED_TEST",
    "provider_language": "rust",
    "authority_default": selected["authority"],
    "side_effect_policy": selected["side_effect"],
    "planned_actions": selected["actions"],
    "promotion_decision": selected["decision"],
    "promotion_score": selected["score"],
    "transport": {
        "current": "cli",
        "target": "vxn",
        "vxn_binding_status": "PENDING"
    },
    "capability_implementation_status": "PENDING_RESOURCE_ADAPTER",
    "entrypoint": "src/main.rs",
    "selection_snapshot": str(selection_path),
}

rustc = shutil.which("rustc")
if not rustc:
    raise SystemExit(fail("RUSTC_LOOKUP", 40))

tmp_dir = Path(tempfile.mkdtemp(prefix="vxs-second-organ-genesis-"))
try:
    tmp_rs = tmp_dir / "main.rs"
    tmp_exe = tmp_dir / ("second-organ.exe" if os.name == "nt" else "second-organ")
    tmp_rs.write_text(rust_source, encoding="utf-8")

    compile_proc = run(
        [rustc, "--edition", "2021", str(tmp_rs), "-O", "-o", str(tmp_exe)],
        cwd=tmp_dir,
    )
    if compile_proc.returncode != 0:
        raise SystemExit(fail(
            "RUST_COMPILE",
            41,
            "STDERR=" + (compile_proc.stderr or "")[-8000:].replace("\n", "\\n"),
        ))

    identity = run([str(tmp_exe), "identity"], cwd=ROOT, timeout=30)
    if (
        identity.returncode != 0
        or f'"resource":"{resource}"' not in identity.stdout
        or '"status":"SCAFFOLDED_TEST"' not in identity.stdout
    ):
        raise SystemExit(fail("IDENTITY_SMOKE", 42))

    selftest = run([str(tmp_exe), "selftest"], cwd=ROOT, timeout=30)
    if (
        selftest.returncode != 0
        or '"selftest":true' not in selftest.stdout
        or f'"resource":"{resource}"' not in selftest.stdout
    ):
        raise SystemExit(fail("SELFTEST_SMOKE", 43))

    selection_dir.mkdir(parents=True, exist_ok=True)
    src_dir.mkdir(parents=True, exist_ok=True)

    selection_path.write_text(
        json.dumps(selection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rs_path.write_text(rust_source, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    persisted_selection = json.loads(selection_path.read_text(encoding="utf-8"))
    persisted_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if persisted_selection.get("selected", {}).get("resource") != resource:
        raise SystemExit(fail("SELECTION_PERSISTENCE", 44))
    if persisted_manifest.get("resource") != resource:
        raise SystemExit(fail("MANIFEST_PERSISTENCE", 45))
    if persisted_manifest.get("capability_implementation_status") != "PENDING_RESOURCE_ADAPTER":
        raise SystemExit(fail("NO_FAKE_CAPABILITY_GUARD", 46))

    print("VXS_SECOND_ORGAN_GENESIS=PASS")
    print("SELECTED_RESOURCE=" + resource)
    print("SELECTED_DECISION=" + selected["decision"])
    print("SELECTED_SCORE=" + ("NONE" if selected["score"] is None else str(selected["score"])))
    print("SELECTED_ACTIONS=" + ",".join(selected["actions"]))
    print("SELECTED_AUTHORITY=" + selected["authority"])
    print("SELECTED_SIDE_EFFECT=" + selected["side_effect"])
    print("ORGAN_ID=" + organ_id)
    print("STATUS=SCAFFOLDED_TEST")
    print("CAPABILITY_IMPLEMENTATION_STATUS=PENDING_RESOURCE_ADAPTER")
    print("RUST_COMPILE=PASS")
    print("IDENTITY_SMOKE=PASS")
    print("SELFTEST_SMOKE=PASS")
    print("POWERSHELL_USED=false")
    print("SELECTION_PATH=" + str(selection_path))
    print("SELECTION_SHA256=" + sha256_file(selection_path))
    print("SOURCE_PATH=" + str(rs_path))
    print("SOURCE_SHA256=" + sha256_file(rs_path))
    print("MANIFEST_PATH=" + str(manifest_path))
    print("MANIFEST_SHA256=" + sha256_file(manifest_path))
    raise SystemExit(0)

finally:
    shutil.rmtree(tmp_dir, ignore_errors=True)
