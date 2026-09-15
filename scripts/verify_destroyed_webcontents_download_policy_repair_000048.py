from pathlib import Path
import subprocess
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
POLICY = ROOT / "src/main/vra/vra-download-destination-policy.ts"
PUBLISHER = ROOT / "scripts/publish_latest_to_vertex_workstation_000047.py"

def safe_emit(value, stream=None):
    stream = stream or sys.stdout
    enc = getattr(stream, "encoding", None) or "utf-8"
    text = str(value).encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    stream.write(text)
    if text and not text.endswith("\n"):
        stream.write("\n")

def check(name, ok, failures):
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def main():
    print("=== VERTEX SESSION PORTAL / DESTROYED WEBCONTENTS REPAIR VERIFY 000048 ===")
    failures = []

    check("POLICY_PRESENT", POLICY.exists(), failures)
    text = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""

    check(
        "SESSION_CAPTURE_SYNCHRONOUS",
        "targetSession = contents.session" in text,
        failures,
    )
    check(
        "ASYNC_CONTENTS_SESSION_ACCESS_RETIRED",
        "setImmediate(() => bindAsLastListener(contents.session))" not in text
        and "setImmediate(() => bindAsLastListener(contents.session" not in text,
        failures,
    )
    check(
        "SCHEDULE_BIND_USES_CAPTURED_SESSION",
        "scheduleBind(targetSession)" in text,
        failures,
    )
    check(
        "MAIN_PROCESS_CRASH_GUARD",
        "try {" in text
        and "console.warn('[VRA DOWNLOAD] session bind skipped'" in text,
        failures,
    )
    check(
        "DID_FINISH_LOAD_CAPTURED_SESSION",
        "contents.on('did-finish-load'" in text
        and "scheduleBind(targetSession)" in text,
        failures,
    )
    check(
        "VRA_SAVE_POLICY_PRESERVED",
        "item.setSavePath(target)" in text
        and "moveCompletedDownload(actualPath, configured)" in text,
        failures,
    )
    check("000047_PUBLISHER_PRESENT", PUBLISHER.exists(), failures)

    if failures:
        print("STATIC_FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    result = subprocess.run(
        [npm, "run", "build"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    safe_emit(result.stdout, sys.stdout)
    if result.stderr:
        safe_emit(result.stderr, sys.stderr)

    check("SOURCE_BUILD", result.returncode == 0, failures)

    if failures:
        raise SystemExit(3)

    print("ROOT_CAUSE=ASYNC_ACCESS_TO_DESTROYED_WEBCONTENTS_SESSION")
    print("REPAIR=CAPTURE_SESSION_SYNCHRONOUSLY_AND_REUSE")
    print("VERTEX_SESSION_PORTAL_DESTROYED_WEBCONTENTS_REPAIR_000048=PASS")

if __name__ == "__main__":
    main()
