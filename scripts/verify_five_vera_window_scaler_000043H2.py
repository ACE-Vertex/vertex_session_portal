from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts/apply_five_vera_window_scaler_000043.py"
BASE_VERIFY = ROOT / "scripts/verify_five_vera_window_scaler_000043.py"

def safe_emit(text: str, stream=None) -> None:
    stream = stream or sys.stdout
    if text is None:
        return
    value = str(text)
    encoding = getattr(stream, "encoding", None) or "utf-8"
    safe = value.encode(encoding, errors="backslashreplace").decode(encoding, errors="replace")
    stream.write(safe)
    if safe and not safe.endswith("\n"):
        stream.write("\n")
    stream.flush()

def check(name: str, ok: bool, failures: list[str]) -> None:
    print(f"{name}={'PASS' if ok else 'FAIL'}")
    if not ok:
        failures.append(name)

def run_python(path: Path) -> int:
    print(f"RUN={sys.executable} {path.relative_to(ROOT)}")
    result = subprocess.run(
        [sys.executable, str(path)],
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
    return result.returncode

def main() -> None:
    print("VERTEX SESSION PORTAL / FIVE VERA WINDOW SCALER REPAIR VERIFY 000043H2")
    print(f"ROOT={ROOT}")

    failures: list[str] = []
    apply_text = APPLY.read_text(encoding="utf-8") if APPLY.exists() else ""
    verify_text = BASE_VERIFY.read_text(encoding="utf-8") if BASE_VERIFY.exists() else ""

    check("BASE_APPLY_PRESENT", APPLY.exists(), failures)
    check("BASE_VERIFY_PRESENT", BASE_VERIFY.exists(), failures)
    check(
        "APPLY_SAFE_EMIT_PRESENT",
        "backslashreplace" in apply_text and "safe_emit(result.stdout" in apply_text,
        failures,
    )
    check(
        "VERIFY_SAFE_EMIT_PRESENT",
        "backslashreplace" in verify_text and "safe_emit(result.stdout" in verify_text,
        failures,
    )
    check(
        "UNSAFE_BUILD_STDOUT_PRINT_RETIRED_APPLY",
        "print(result.stdout)" not in apply_text,
        failures,
    )
    check(
        "UNSAFE_BUILD_STDOUT_PRINT_RETIRED_VERIFY",
        "print(result.stdout)" not in verify_text,
        failures,
    )

    if failures:
        raise SystemExit(2)

    base_code = run_python(BASE_VERIFY)
    check("BASE_000043_VERIFY", base_code == 0, failures)

    if failures:
        raise SystemExit(3)

    print("VERTEX_SESSION_PORTAL_FIVE_VERA_WINDOW_SCALER_000043H2=PASS")

if __name__ == "__main__":
    main()
