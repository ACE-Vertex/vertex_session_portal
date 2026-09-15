from pathlib import Path
import re
import sys
import traceback

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
TS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"
CONTRACTS = ROOT / "src/shared/contracts.ts"

def safe_text(value: object) -> str:
    text = str(value)
    # Keep logs readable on Windows even if the runner overrides console encoding.
    return text.encode("ascii", "backslashreplace").decode("ascii")

def outln(value: object = "") -> None:
    print(safe_text(value))

def read(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"MISSING:{path}")
    return path.read_text(encoding="utf-8-sig").splitlines()

def merge_ranges(ranges, total):
    cooked = []
    for a, b in ranges:
        a = max(1, a)
        b = min(total, b)
        if not cooked or a > cooked[-1][1] + 1:
            cooked.append([a, b])
        else:
            cooked[-1][1] = max(cooked[-1][1], b)
    return cooked

def windows(lines, patterns, before=12, after=20, cap=30):
    hits = []
    rx = [re.compile(p, re.I) for p in patterns]
    for i, line in enumerate(lines, 1):
        if any(r.search(line) for r in rx):
            hits.append(i)
    ranges = merge_ranges([(i-before, i+after) for i in hits[:cap]], len(lines))
    return hits, ranges

def emit(label, path, lines, patterns, before=12, after=20, cap=30):
    hits, ranges = windows(lines, patterns, before, after, cap)
    outln(f"=== {label}_META ===")
    outln(f"PATH={path}")
    outln(f"LINES={len(lines)}")
    outln(f"HITS={hits[:cap]}")
    for n, (a, b) in enumerate(ranges, 1):
        outln(f"--- {label}_WINDOW_{n} lines={a}-{b} ---")
        for i in range(a, b + 1):
            outln(f"{i:05d}|{lines[i-1]}")
    outln(f"=== {label}_END ===")

try:
    ts = read(TS)
    css = read(CSS)
    contracts = read(CONTRACTS)

    emit(
        "TS", TS, ts,
        [
            r"workstationLastError", r"\berror\b", r"workstationEvidenceReturnState",
            r"workstationJobState", r"correlationId", r"originVera", r"originSession",
            r"originWindow", r"artifactId", r"jobId", r"evidenceIdentity",
            r"<button", r"createElement\(['\"]button", r"addEventListener\(['\"]click",
            r"querySelectorAll.*button", r"class=.*action", r"data-.*action",
            r"\brender[A-Za-z0-9_]*\s*\(", r"innerHTML\s*=", r"clipboard"
        ],
        10, 18, 40
    )

    emit(
        "CSS", CSS, css,
        [
            r"\.card", r"\.actions", r"\.action", r"button", r"height", r"min-height",
            r"max-height", r"grid", r"flex", r"error", r"status", r"copy"
        ],
        8, 14, 40
    )

    emit(
        "CONTRACTS", CONTRACTS, contracts,
        [
            r"interface VraDispatchCard", r"type VraDispatchCard",
            r"workstationLastError", r"workstationEvidenceReturnState",
            r"correlationId", r"originVera", r"originSession", r"originWindow",
            r"artifactId", r"jobId", r"projectName", r"evidenceIdentity", r"\berror\b"
        ],
        8, 16, 40
    )

    outln("READ_ONLY=PASS")
    outln("NO_PRODUCTION_MUTATION=PASS")
    outln("WINDOWS_CONSOLE_SAFE_OUTPUT=PASS")
    outln("PURPOSE=EXACT_SOURCE_FOR_ONE_SMALL_ERROR_COPY_BUTTON")
except Exception as exc:
    outln("RAY_SCRIPT_FAILURE=YES")
    outln(f"TYPE={type(exc).__name__}")
    outln(f"MESSAGE={exc}")
    for line in traceback.format_exc().splitlines():
        outln(line)
    raise
