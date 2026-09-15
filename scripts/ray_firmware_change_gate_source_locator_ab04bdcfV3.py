from pathlib import Path
import os

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

SEARCH_ROOTS = [
    ROOT / "src",
    ROOT / "scripts",
]

TEXT_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".scss", ".css", ".html", ".json", ".md", ".txt", ".py"
}

TERMS = [
    "firmware",
    "firmware change gate",
    "change gate",
    "fw ready",
    "pending change queue",
    "deep ray",
    "red arm",
    "final commit",
    "decision event",
    "signed approval",
    "registrar",
]

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def finish(code, label):
    emit("RAY_CLASSIFICATION=" + label)
    emit("PRODUCTION_MUTATION=NONE")
    raise SystemExit(code)

present_roots = [p for p in SEARCH_ROOTS if p.exists()]
if not present_roots:
    finish(44, "NO_SEARCH_ROOTS")

hits = []
for base in present_roots:
    for p in base.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if p.stat().st_size > 5 * 1024 * 1024:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        low = text.lower()
        matched = [t for t in TERMS if t in low]
        name_low = p.name.lower()
        if matched or "firmware" in name_low or ("change" in name_low and "gate" in name_low):
            hits.append((p, text, matched))

emit(f"HIT_FILE_COUNT={len(hits)}")

for p, text, matched in sorted(hits, key=lambda x: x[0].as_posix()):
    rel = p.relative_to(ROOT).as_posix()
    emit(f"FILE={rel}")
    emit("MATCHED_TERMS=" + (",".join(matched) if matched else "-"))
    lines = text.splitlines()
    shown = 0
    for idx, line in enumerate(lines, 1):
        ll = line.lower()
        if any(t in ll for t in TERMS):
            emit(f"  L{idx}: {line}")
            shown += 1
            if shown >= 40:
                emit("  ...TRUNCATED...")
                break

# Also list filename-only candidates even when content has no marker.
filename_candidates = []
for base in present_roots:
    for p in base.rglob("*"):
        if p.is_file():
            nl = p.name.lower()
            if "firmware" in nl or ("change" in nl and "gate" in nl):
                filename_candidates.append(p.relative_to(ROOT).as_posix())

emit("FILENAME_CANDIDATES=" + (";".join(sorted(set(filename_candidates))) if filename_candidates else "-"))

# MainFrame exact candidates.
main_candidates = []
for p in (ROOT / "src").rglob("*") if (ROOT / "src").exists() else []:
    if not p.is_file() or p.suffix.lower() not in {".ts", ".tsx", ".js", ".jsx"}:
        continue
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue
    low = text.lower()
    if "mainframe" in p.name.lower() or "class mainframe" in low or ("main-frame" in low and "customelements.define" in low):
        main_candidates.append((p, text))

emit(f"MAINFRAME_CANDIDATE_COUNT={len(main_candidates)}")
for p, text in main_candidates:
    rel = p.relative_to(ROOT).as_posix()
    emit(f"MAINFRAME={rel}")
    for idx, line in enumerate(text.splitlines(), 1):
        ll = line.lower()
        if "firmware" in ll or "gate" in ll or "customelements.define" in ll or "main-frame" in ll:
            emit(f"  L{idx}: {line}")

if not hits and not filename_candidates:
    finish(40, "NO_FIRMWARE_GATE_ARTIFACTS_FOUND")

has_src_hit = any(str(p).lower().find(str((ROOT / "src")).lower()) == 0 for p, _, _ in hits)
has_strong_marker = any(
    any(t in matched for t in ("firmware change gate", "fw ready", "pending change queue", "deep ray"))
    for _, _, matched in hits
)

if has_src_hit and has_strong_marker:
    finish(0, "FIRMWARE_GATE_SOURCE_LOCATED")

if has_src_hit:
    finish(41, "ONLY_WEAK_FIRMWARE_GATE_SOURCE_MARKERS_FOUND")

finish(42, "FIRMWARE_GATE_ARTIFACTS_ONLY_OUTSIDE_SRC")
