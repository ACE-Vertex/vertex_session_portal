from pathlib import Path
import re, sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SRC = ROOT / "src"
PREV_LOG = Path(r"G:\Vertex_Project\Development\vertex_workstation\runtime\lanes\lane-06\logs\stage-vertex-error-card-copy-return-coupling-ray-000074V3-1789381945498-698\verify")

# Force ASCII-safe evidence output. All non-ASCII source/log characters are escaped.
def safe(value):
    if value is None:
        return ""
    return str(value).encode("ascii", "backslashreplace").decode("ascii")

def emit(value=""):
    print(safe(value))

emit("=== PREVIOUS 000074 STDOUT/STDERR ===")
for name in ("000-stdout.log", "000-stderr.log"):
    p = PREV_LOG / name
    emit(f"LOG={p}")
    if p.exists():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            emit(f"READ_ERROR={type(e).__name__}:{e}")
            continue
        emit(text[-12000:])
    else:
        emit("MISSING")

CATEGORIES = {
    "COPY": [
        r"\bcopy\b", r"clipboard", r"writeText", r"copyToClipboard",
        r"copyEvidence", r"copyError", r"copy.*error", r"error.*copy"
    ],
    "FAILED": [
        r"\bFAILED\b", r"\bfailed\b", r"verified\s*[:=!]=?\s*false",
        r"result\s*[:=!]=?\s*['\"]failed['\"]", r"workstationJobState"
    ],
    "RETURN": [
        r"RETURN_QUEUED", r"RETURNED", r"return-queue",
        r"evidence_return_state", r"workstationEvidenceReturnState",
        r"enqueue.*return", r"return.*evidence", r"deliver.*evidence",
        r"evidence.*deliver", r"returned_at", r"returnedAt"
    ],
    "ERROR_CARD": [
        r"ErrorCard", r"error card", r"error-card", r"failed card",
        r"failure card", r"VRA.*error", r"error.*VRA", r"workstation.*error"
    ],
    "SESSION": [
        r"source_web_contents_id", r"sourceWebContentsId",
        r"origin_session", r"originSession", r"origin_window",
        r"webContents", r"session.*deliver", r"deliver.*session"
    ],
}

TEXT_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
IGNORE_PARTS = {"node_modules", "dist", "build", "out", "coverage", ".git"}
compiled = {k: [re.compile(p, re.I) for p in v] for k, v in CATEGORIES.items()}

def owner(rel):
    low = rel.lower()
    if low.startswith("src/main/"):
        return "MAIN"
    if low.startswith("src/renderer/"):
        return "RENDERER"
    if low.startswith("src/preload/"):
        return "PRELOAD"
    return "OTHER"

def cats_for(line):
    return [cat for cat, regs in compiled.items() if any(r.search(line) for r in regs)]

if not SRC.exists():
    emit("RAY_RESULT=SOURCE_ROOT_MISSING")
    raise SystemExit(0)

candidates = []
files_scanned = 0

for path in sorted(SRC.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in TEXT_EXTS:
        continue
    if any(part in IGNORE_PARTS for part in path.parts):
        continue
    files_scanned += 1
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        continue

    file_cats = set()
    hits = []
    for i, line in enumerate(lines):
        cats = cats_for(line)
        if cats:
            file_cats.update(cats)
            hits.append((i, cats))

    score = 0
    if "COPY" in file_cats and "FAILED" in file_cats: score += 4
    if "COPY" in file_cats and "RETURN" in file_cats: score += 5
    if "COPY" in file_cats and "ERROR_CARD" in file_cats: score += 4
    if "FAILED" in file_cats and "RETURN" in file_cats: score += 5
    if "RETURN" in file_cats and "SESSION" in file_cats: score += 3
    if {"COPY","FAILED","RETURN"}.issubset(file_cats): score += 8

    if score:
        rel = path.relative_to(ROOT).as_posix()
        candidates.append((score, rel, path, lines, hits, sorted(file_cats)))

candidates.sort(key=lambda x: (-x[0], x[1]))

emit("=== COUPLING RAY ===")
emit(f"FILES_SCANNED={files_scanned}")
emit(f"CANDIDATE_FILES={len(candidates)}")

for rank, (score, rel, path, lines, hits, file_cats) in enumerate(candidates[:20], 1):
    emit(f"\n### CANDIDATE rank={rank} score={score} owner={owner(rel)} file={rel}")
    emit("FILE_CATEGORIES=" + ",".join(file_cats))

    emitted = 0
    for i, cats in hits:
        if "COPY" in cats or "RETURN" in cats or ("FAILED" in cats and "RETURN" in file_cats):
            start = max(0, i - 3)
            end = min(len(lines), i + 4)
            emit(f"--- {rel}:{i+1} [{','.join(cats)}] ---")
            for j in range(start, end):
                prefix = ">>" if j == i else "  "
                emit(f"{prefix}{j+1:05d}: {lines[j]}")
            emitted += 1
        if emitted >= 8:
            break

    for i, line in enumerate(lines):
        if re.search(r"\bif\b.*\b(success|succeeded|verified)\b", line, re.I):
            window = "\n".join(lines[max(0, i-8):min(len(lines), i+12)])
            if any(r.search(window) for r in compiled["RETURN"]) or any(r.search(window) for r in compiled["COPY"]):
                emit(f"SUCCESS_ONLY_GATE_CANDIDATE={rel}:{i+1}")
                for j in range(max(0, i-4), min(len(lines), i+7)):
                    prefix = ">>" if j == i else "  "
                    emit(f"{prefix}{j+1:05d}: {lines[j]}")

    for i, line in enumerate(lines):
        if any(r.search(line) for r in compiled["FAILED"]):
            window = "\n".join(lines[max(0, i-10):min(len(lines), i+18)])
            has_copy = any(r.search(window) for r in compiled["COPY"])
            has_return = any(r.search(window) for r in compiled["RETURN"])
            if has_copy and not has_return:
                emit(f"FAILED_COPY_WITHOUT_RETURN_NEARBY={rel}:{i+1}")

emit("=== SUMMARY ===")
if candidates:
    top = candidates[0]
    emit(f"TOP_OWNER={owner(top[1])}")
    emit(f"TOP_FILE={top[1]}")
    emit(f"TOP_SCORE={top[0]}")
    emit("RAY_RESULT=COUPLING_CANDIDATES_FOUND")
else:
    emit("RAY_RESULT=NO_COUPLING_CANDIDATES")
emit("PRODUCTION_MUTATION=NONE")
raise SystemExit(0)
