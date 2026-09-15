from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

EXPECTED_PS_VERSION = "7.6.6"
PLAN_SCHEMA = "vertex-vxs/native-promotion-plan-1"
ORGAN_SCHEMA = "vertex-vxs/native-organ-1"

RUST_SOURCE = "use std::env;\nuse std::fs;\nuse std::path::Path;\n\nfn esc(s: &str) -> String {\n    s.replace('\\\\', \"\\\\\\\\\").replace('\"', \"\\\\\\\"\")\n}\n\nfn print_system() {\n    let cwd = env::current_dir()\n        .map(|p| p.display().to_string())\n        .unwrap_or_default();\n\n    println!(\n        \"{{\\\"schema\\\":\\\"vertex-vxs/native-organ-output-1\\\",\\\"organ\\\":\\\"system\\\",\\\"action\\\":\\\"observe\\\",\\\"os\\\":\\\"{}\\\",\\\"arch\\\":\\\"{}\\\",\\\"family\\\":\\\"{}\\\",\\\"cwd\\\":\\\"{}\\\",\\\"pid\\\":{}}}\",\n        esc(env::consts::OS),\n        esc(env::consts::ARCH),\n        esc(env::consts::FAMILY),\n        esc(&cwd),\n        std::process::id()\n    );\n}\n\nfn print_exists(target: &str) {\n    println!(\n        \"{{\\\"schema\\\":\\\"vertex-vxs/native-organ-output-1\\\",\\\"organ\\\":\\\"filesystem\\\",\\\"action\\\":\\\"exists\\\",\\\"target\\\":\\\"{}\\\",\\\"exists\\\":{}}}\",\n        esc(target),\n        Path::new(target).exists()\n    );\n}\n\nfn print_metadata(target: &str) -> Result<(), String> {\n    let meta = fs::metadata(target).map_err(|e| e.to_string())?;\n    let file_type = if meta.is_file() {\n        \"file\"\n    } else if meta.is_dir() {\n        \"directory\"\n    } else {\n        \"other\"\n    };\n\n    let modified_ms = meta.modified()\n        .ok()\n        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())\n        .map(|d| d.as_millis().to_string())\n        .unwrap_or_else(|| \"null\".to_string());\n\n    println!(\n        \"{{\\\"schema\\\":\\\"vertex-vxs/native-organ-output-1\\\",\\\"organ\\\":\\\"filesystem\\\",\\\"action\\\":\\\"metadata\\\",\\\"target\\\":\\\"{}\\\",\\\"type\\\":\\\"{}\\\",\\\"readonly\\\":{},\\\"bytes\\\":{},\\\"modified_unix_ms\\\":{}}}\",\n        esc(target),\n        file_type,\n        meta.permissions().readonly(),\n        meta.len(),\n        modified_ms\n    );\n    Ok(())\n}\n\nfn print_list(target: &str) -> Result<(), String> {\n    let mut entries = Vec::new();\n    for entry in fs::read_dir(target).map_err(|e| e.to_string())?.take(128) {\n        let entry = entry.map_err(|e| e.to_string())?;\n        let name = entry.file_name().to_string_lossy().to_string();\n        entries.push(format!(\"\\\"{}\\\"\", esc(&name)));\n    }\n\n    println!(\n        \"{{\\\"schema\\\":\\\"vertex-vxs/native-organ-output-1\\\",\\\"organ\\\":\\\"filesystem\\\",\\\"action\\\":\\\"list\\\",\\\"target\\\":\\\"{}\\\",\\\"entries\\\":[{}]}}\",\n        esc(target),\n        entries.join(\",\")\n    );\n    Ok(())\n}\n\nfn usage() {\n    eprintln!(\"usage: vxs-native-organ <system|fs-exists|fs-meta|fs-list> [target]\");\n}\n\nfn main() {\n    let args: Vec<String> = env::args().collect();\n    let result = match args.get(1).map(String::as_str) {\n        Some(\"system\") => {\n            print_system();\n            Ok(())\n        }\n        Some(\"fs-exists\") => {\n            if let Some(target) = args.get(2) {\n                print_exists(target);\n                Ok(())\n            } else {\n                Err(\"target required\".to_string())\n            }\n        }\n        Some(\"fs-meta\") => {\n            if let Some(target) = args.get(2) {\n                print_metadata(target)\n            } else {\n                Err(\"target required\".to_string())\n            }\n        }\n        Some(\"fs-list\") => {\n            if let Some(target) = args.get(2) {\n                print_list(target)\n            } else {\n                Err(\"target required\".to_string())\n            }\n        }\n        _ => {\n            usage();\n            Err(\"unknown command\".to_string())\n        }\n    };\n\n    if let Err(err) = result {\n        eprintln!(\"{}\", err);\n        std::process::exit(2);\n    }\n}\n"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(args: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
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


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    predation_dir = root / "runtime" / "vxs" / "predation"
    plan_path = predation_dir / f"powershell-{EXPECTED_PS_VERSION}-native-promotion-plan.json"

    if not plan_path.is_file():
        print("VXS_NATIVE_ORGAN=FAIL")
        print("STAGE=PLAN_LOOKUP")
        print("EXPECTED=" + str(plan_path))
        return 20

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print("VXS_NATIVE_ORGAN=FAIL")
        print("STAGE=PLAN_PARSE")
        print("ERROR=" + type(exc).__name__ + ":" + str(exc))
        return 21

    if plan.get("schema") != PLAN_SCHEMA:
        print("VXS_NATIVE_ORGAN=FAIL")
        print("STAGE=PLAN_SCHEMA")
        print("FOUND=" + str(plan.get("schema")))
        return 22

    runtime_version = str(plan.get("runtime_version") or "")
    if runtime_version != EXPECTED_PS_VERSION:
        print("VXS_NATIVE_ORGAN=FAIL")
        print("STAGE=RUNTIME_VERSION")
        print("FOUND=" + runtime_version)
        return 23

    organs = plan.get("native_organs") or []
    if not isinstance(organs, list):
        print("VXS_NATIVE_ORGAN=FAIL")
        print("STAGE=ORGAN_PLAN")
        return 24

    eligible = []
    for organ in organs:
        resource = str(organ.get("resource") or "")
        if resource in {"FILESYSTEM", "SYSTEM"}:
            eligible.append(organ)

    organ_root = predation_dir / "native-organs" / "vxs-native-observer"
    src_dir = organ_root / "src"
    rs_path = src_dir / "main.rs"
    manifest_path = organ_root / "organ.json"

    manifest = {
        "schema": ORGAN_SCHEMA,
        "organ_id": "vxs-native-observer",
        "status": "MATERIALIZED_TEST",
        "provider_language": "rust",
        "transport": {
            "current": "cli",
            "target": "vxn",
            "vxn_binding_status": "PENDING"
        },
        "authority_default": "AUTO_SAFE",
        "side_effect_policy": "NONE_ONLY",
        "resources": ["FILESYSTEM", "SYSTEM"],
        "actions": ["OBSERVE", "TEST", "FIND", "MEASURE"],
        "source_plan": {
            "path": str(plan_path),
            "sha256": sha256_file(plan_path)
        },
        "promotion_plan_matches": eligible,
        "entrypoint": "src/main.rs"
    }

    tmp_dir = Path(tempfile.mkdtemp(prefix="vxs-native-organ-"))
    try:
        tmp_rs = tmp_dir / "main.rs"
        tmp_exe = tmp_dir / ("vxs-native-organ.exe" if os.name == "nt" else "vxs-native-organ")
        tmp_rs.write_text(RUST_SOURCE, encoding="utf-8")

        rustc = shutil.which("rustc")
        if not rustc:
            print("VXS_NATIVE_ORGAN=FAIL")
            print("STAGE=RUSTC_LOOKUP")
            return 40

        compile_proc = run(
            [rustc, "--edition", "2021", str(tmp_rs), "-O", "-o", str(tmp_exe)],
            cwd=tmp_dir,
            timeout=120,
        )
        if compile_proc.returncode != 0:
            print("VXS_NATIVE_ORGAN=FAIL")
            print("STAGE=RUST_COMPILE")
            print("EXIT_CODE=" + str(compile_proc.returncode))
            if compile_proc.stdout:
                print("STDOUT=" + compile_proc.stdout[-4000:].replace("\n", "\\n"))
            if compile_proc.stderr:
                print("STDERR=" + compile_proc.stderr[-8000:].replace("\n", "\\n"))
            return 41

        system_proc = run([str(tmp_exe), "system"], cwd=root)
        if system_proc.returncode != 0 or '"organ":"system"' not in system_proc.stdout:
            print("VXS_NATIVE_ORGAN=FAIL")
            print("STAGE=RUST_SYSTEM_SMOKE")
            return 42

        meta_proc = run([str(tmp_exe), "fs-meta", str(plan_path)], cwd=root)
        if meta_proc.returncode != 0 or '"organ":"filesystem"' not in meta_proc.stdout:
            print("VXS_NATIVE_ORGAN=FAIL")
            print("STAGE=RUST_FILESYSTEM_SMOKE")
            return 43

        src_dir.mkdir(parents=True, exist_ok=True)
        rs_path.write_text(RUST_SOURCE, encoding="utf-8")
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        persisted_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if persisted_manifest.get("schema") != ORGAN_SCHEMA:
            print("VXS_NATIVE_ORGAN=FAIL")
            print("STAGE=PERSISTED_MANIFEST")
            return 44

        if rs_path.read_text(encoding="utf-8") != RUST_SOURCE:
            print("VXS_NATIVE_ORGAN=FAIL")
            print("STAGE=PERSISTED_SOURCE")
            return 45

        print("VXS_NATIVE_ORGAN=PASS")
        print("PS_VERSION=" + runtime_version)
        print("ORGAN_ID=vxs-native-observer")
        print("RUSTC=" + rustc)
        print("SOURCE_PATH=" + str(rs_path))
        print("SOURCE_SHA256=" + sha256_file(rs_path))
        print("MANIFEST_PATH=" + str(manifest_path))
        print("MANIFEST_SHA256=" + sha256_file(manifest_path))
        print("PROMOTION_MATCH_COUNT=" + str(len(eligible)))
        print("SYSTEM_SMOKE=PASS")
        print("FILESYSTEM_SMOKE=PASS")
        print("POWERSHELL_USED=false")
        print("VXN_BINDING_STATUS=PENDING")
        return 0
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
