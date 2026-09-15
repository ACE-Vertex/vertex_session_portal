from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ORGAN_SCHEMA = "vertex-vxs/native-organ-1"
BINDING_SCHEMA = "vertex-vxs/native-provider-binding-1"
ORGAN_ID = "vxs-native-observer"


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


def parse_json_line(text: str) -> dict:
    line = text.strip().splitlines()[-1] if text.strip() else ""
    return json.loads(line)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    predation_dir = root / "runtime" / "vxs" / "predation"
    organ_root = predation_dir / "native-organs" / ORGAN_ID

    source_rs = organ_root / "src" / "main.rs"
    organ_manifest = organ_root / "organ.json"

    if not source_rs.is_file():
        print("VXS_TRANSPLANT=FAIL")
        print("STAGE=SOURCE_LOOKUP")
        print("EXPECTED=" + str(source_rs))
        return 20

    if not organ_manifest.is_file():
        print("VXS_TRANSPLANT=FAIL")
        print("STAGE=ORGAN_MANIFEST_LOOKUP")
        print("EXPECTED=" + str(organ_manifest))
        return 21

    try:
        organ = json.loads(organ_manifest.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print("VXS_TRANSPLANT=FAIL")
        print("STAGE=ORGAN_MANIFEST_PARSE")
        print("ERROR=" + type(exc).__name__ + ":" + str(exc))
        return 22

    if organ.get("schema") != ORGAN_SCHEMA:
        print("VXS_TRANSPLANT=FAIL")
        print("STAGE=ORGAN_SCHEMA")
        print("FOUND=" + str(organ.get("schema")))
        return 23

    if organ.get("organ_id") != ORGAN_ID:
        print("VXS_TRANSPLANT=FAIL")
        print("STAGE=ORGAN_ID")
        print("FOUND=" + str(organ.get("organ_id")))
        return 24

    rustc = shutil.which("rustc")
    if not rustc:
        print("VXS_TRANSPLANT=FAIL")
        print("STAGE=RUSTC_LOOKUP")
        return 40

    native_root = root / "runtime" / "vxs" / "native"
    bin_dir = native_root / "bin"
    provider_dir = native_root / "providers"
    bin_dir.mkdir(parents=True, exist_ok=True)
    provider_dir.mkdir(parents=True, exist_ok=True)

    exe_name = ORGAN_ID + (".exe" if os.name == "nt" else "")
    final_exe = bin_dir / exe_name
    binding_path = provider_dir / f"{ORGAN_ID}.json"

    tmp_dir = Path(tempfile.mkdtemp(prefix="vxs-native-transplant-"))
    try:
        tmp_exe = tmp_dir / exe_name

        compile_proc = run(
            [rustc, "--edition", "2021", str(source_rs), "-O", "-o", str(tmp_exe)],
            cwd=root,
            timeout=120,
        )
        if compile_proc.returncode != 0:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=RUST_COMPILE")
            print("EXIT_CODE=" + str(compile_proc.returncode))
            if compile_proc.stdout:
                print("STDOUT=" + compile_proc.stdout[-4000:].replace("\n", "\\n"))
            if compile_proc.stderr:
                print("STDERR=" + compile_proc.stderr[-8000:].replace("\n", "\\n"))
            return 41

        # Verify the physical organ before transplant.
        sys_proc = run([str(tmp_exe), "system"], cwd=root)
        if sys_proc.returncode != 0:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=SYSTEM_SMOKE")
            return 42
        try:
            sys_json = parse_json_line(sys_proc.stdout)
        except Exception:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=SYSTEM_OUTPUT_PARSE")
            return 43
        if sys_json.get("organ") != "system" or sys_json.get("action") != "observe":
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=SYSTEM_OUTPUT_CONTRACT")
            return 44

        fs_proc = run([str(tmp_exe), "fs-meta", str(organ_manifest)], cwd=root)
        if fs_proc.returncode != 0:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=FILESYSTEM_SMOKE")
            return 45
        try:
            fs_json = parse_json_line(fs_proc.stdout)
        except Exception:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=FILESYSTEM_OUTPUT_PARSE")
            return 46
        if fs_json.get("organ") != "filesystem" or fs_json.get("action") != "metadata":
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=FILESYSTEM_OUTPUT_CONTRACT")
            return 47

        tmp_sha = sha256_file(tmp_exe)

        # Transplant: atomic binary promotion.
        staged_exe = final_exe.with_suffix(final_exe.suffix + ".new")
        shutil.copy2(tmp_exe, staged_exe)
        if sha256_file(staged_exe) != tmp_sha:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=BINARY_STAGE_HASH")
            return 48
        os.replace(staged_exe, final_exe)

        # Re-run from its permanent location.
        permanent_proc = run([str(final_exe), "system"], cwd=root)
        if permanent_proc.returncode != 0:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=PERMANENT_BINARY_SMOKE")
            return 49

        permanent_json = parse_json_line(permanent_proc.stdout)
        if permanent_json.get("schema") != "vertex-vxs/native-organ-output-1":
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=PERMANENT_OUTPUT_SCHEMA")
            return 50

        binding = {
            "schema": BINDING_SCHEMA,
            "provider_id": ORGAN_ID,
            "state": "CONNECTED_TEST",
            "binary": {
                "path": str(final_exe),
                "sha256": sha256_file(final_exe),
            },
            "source": {
                "path": str(source_rs),
                "sha256": sha256_file(source_rs),
                "organ_manifest": str(organ_manifest),
                "organ_manifest_sha256": sha256_file(organ_manifest),
            },
            "authority": {
                "default": "AUTO_SAFE",
                "allowed": ["AUTO_SAFE"],
                "human_apply_required_for_mutation": True,
            },
            "side_effect_policy": "NONE_ONLY",
            "capabilities": {
                "system": ["observe"],
                "filesystem": ["exists", "metadata", "list"],
            },
            "routing": {
                "priority": "NATIVE_FIRST",
                "fallback": "POWERSHELL",
                "fallback_status": "DECLARED_NOT_WIRED",
            },
            "transport": {
                "current": "native-process-json",
                "target": "vxn",
                "vxn_binding_status": "PENDING_CONTRACT",
            },
        }

        tmp_binding = binding_path.with_suffix(binding_path.suffix + ".tmp")
        tmp_binding.write_text(
            json.dumps(binding, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Durable descriptor verification before promotion.
        reread = json.loads(tmp_binding.read_text(encoding="utf-8"))
        if reread.get("schema") != BINDING_SCHEMA:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=BINDING_SCHEMA")
            return 51
        if reread.get("provider_id") != ORGAN_ID:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=BINDING_PROVIDER_ID")
            return 52
        if reread.get("binary", {}).get("sha256") != sha256_file(final_exe):
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=BINDING_BINARY_HASH")
            return 53

        os.replace(tmp_binding, binding_path)

        # Final connection smoke from descriptor.
        persisted_binding = json.loads(binding_path.read_text(encoding="utf-8"))
        descriptor_binary = Path(persisted_binding["binary"]["path"])
        if not descriptor_binary.is_file():
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=DESCRIPTOR_BINARY_LOOKUP")
            return 54

        connect_proc = run([str(descriptor_binary), "fs-exists", str(source_rs)], cwd=root)
        if connect_proc.returncode != 0:
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=DESCRIPTOR_ROUTE_SMOKE")
            return 55

        connect_json = parse_json_line(connect_proc.stdout)
        if connect_json.get("organ") != "filesystem" or connect_json.get("action") != "exists":
            print("VXS_TRANSPLANT=FAIL")
            print("STAGE=DESCRIPTOR_ROUTE_OUTPUT")
            return 56

        print("VXS_TRANSPLANT=PASS")
        print("ORGAN_ID=" + ORGAN_ID)
        print("BINARY_PATH=" + str(final_exe))
        print("BINARY_SHA256=" + sha256_file(final_exe))
        print("BINDING_PATH=" + str(binding_path))
        print("BINDING_SHA256=" + sha256_file(binding_path))
        print("SYSTEM_SMOKE=PASS")
        print("FILESYSTEM_SMOKE=PASS")
        print("PERMANENT_BINARY_SMOKE=PASS")
        print("DESCRIPTOR_ROUTE_SMOKE=PASS")
        print("POWERSHELL_USED=false")
        print("ROUTING_PRIORITY=NATIVE_FIRST")
        print("POWERSHELL_FALLBACK=DECLARED_NOT_WIRED")
        print("VXN_BINDING_STATUS=PENDING_CONTRACT")
        return 0

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
