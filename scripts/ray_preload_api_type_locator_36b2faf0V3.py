from pathlib import Path
import re

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
PRELOAD_ROOT = ROOT / "src/preload"
SRC = ROOT / "src"

def emit(s=""):
    print(str(s).encode("ascii", "backslashreplace").decode("ascii"))

def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()

def show(path: Path, text: str, start: int, end: int):
    lines = text.splitlines()
    start = max(1, start)
    end = min(len(lines), end)
    emit(f"=== {rel(path)} L{start}-L{end} ===")
    for n in range(start, end + 1):
        emit(f"{n:04d}: {lines[n-1]}")
    emit(f"=== END {rel(path)} ===")

candidates = []
for path in PRELOAD_ROOT.rglob("*.ts"):
    text = path.read_text(encoding="utf-8", errors="replace")
    if "exposeInMainWorld" in text and "vertexPortal" in text:
        candidates.append((path, text))

emit("PRELOAD_CANDIDATE_COUNT=" + str(len(candidates)))
if len(candidates) != 1:
    emit("RAY_CLASSIFICATION=PRELOAD_EXPOSURE_NOT_UNIQUE")
    raise SystemExit(61)

preload_path, preload_text = candidates[0]
emit("PRELOAD=" + rel(preload_path))

variable = re.search(
    r"contextBridge\.exposeInMainWorld\(\s*['\"]vertexPortal['\"]\s*,\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)",
    preload_text,
    re.S,
)
literal = re.search(
    r"contextBridge\.exposeInMainWorld\(\s*['\"]vertexPortal['\"]\s*,\s*\{",
    preload_text,
    re.S,
)

api_name = None
annotation = None
if variable:
    api_name = variable.group(1)
    emit("EXPOSURE_SHAPE=NAMED_OBJECT")
    emit("API_OBJECT_NAME=" + api_name)

    m = re.search(
        rf"(?:const|let|var)\s+{re.escape(api_name)}(?P<annotation>\s*:[^=]+)?\s*=\s*\{{",
        preload_text,
        re.S,
    )
    if not m:
        emit("RAY_CLASSIFICATION=API_OBJECT_DEFINITION_NOT_FOUND")
        raise SystemExit(62)

    annotation = (m.group("annotation") or "").strip()
    emit("API_OBJECT_TYPE_ANNOTATION=" + (annotation if annotation else "<inferred>"))

    line = preload_text[:m.start()].count("\n") + 1
    show(preload_path, preload_text, line - 16, line + 90)

elif literal:
    emit("EXPOSURE_SHAPE=INLINE_LITERAL")
    line = preload_text[:literal.start()].count("\n") + 1
    show(preload_path, preload_text, line - 16, line + 90)
else:
    emit("RAY_CLASSIFICATION=UNSUPPORTED_EXPOSURE_SHAPE")
    raise SystemExit(63)

# Extract type name from annotation such as ": VertexPortalApi" or ": Readonly<VertexPortalApi>".
type_names = set()
if annotation:
    for name in re.findall(r"\b[A-Z][A-Za-z0-9_$]*\b", annotation):
        if name not in {"Readonly", "Partial", "Record", "Promise", "Array"}:
            type_names.add(name)

# Search all src TS/TSX for likely API type declarations and Window augmentation.
type_hits = []
window_hits = []
portal_hits = []

for path in SRC.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".ts", ".tsx", ".d.ts"}:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    low = text.lower()

    if "vertexportal" in low or "vertexportalapi" in low:
        portal_hits.append((path, text))

    for type_name in type_names:
        patterns = [
            rf"\binterface\s+{re.escape(type_name)}\b",
            rf"\btype\s+{re.escape(type_name)}\b",
            rf"\bexport\s+interface\s+{re.escape(type_name)}\b",
            rf"\bexport\s+type\s+{re.escape(type_name)}\b",
        ]
        if any(re.search(pat, text) for pat in patterns):
            type_hits.append((type_name, path, text))

    if re.search(r"\binterface\s+Window\b", text) and "vertexPortal" in text:
        window_hits.append((path, text))

emit("ANNOTATION_TYPE_NAMES=" + (",".join(sorted(type_names)) if type_names else "-"))
emit("TYPE_DECLARATION_HIT_COUNT=" + str(len(type_hits)))
for type_name, path, text in type_hits[:12]:
    emit("TYPE_DECLARATION=" + type_name + "@" + rel(path))
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        if re.search(rf"\b(interface|type)\s+{re.escape(type_name)}\b", line):
            show(path, text, idx - 8, idx + 120)
            break

emit("WINDOW_AUGMENTATION_HIT_COUNT=" + str(len(window_hits)))
for path, text in window_hits[:8]:
    emit("WINDOW_AUGMENTATION=" + rel(path))
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        if "vertexPortal" in line:
            show(path, text, idx - 16, idx + 50)
            break

emit("VERTEXPORTAL_TEXT_HIT_COUNT=" + str(len(portal_hits)))
for path, text in portal_hits[:10]:
    emit("VERTEXPORTAL_HIT=" + rel(path))

# Classify exact patch shape.
if type_hits:
    emit("RAY_CLASSIFICATION=PRELOAD_API_TYPE_DECLARATION_LOCATED")
    raise SystemExit(0)

if variable and annotation:
    emit("RAY_CLASSIFICATION=TYPED_OBJECT_ANNOTATION_UNRESOLVED")
    raise SystemExit(71)

if window_hits:
    emit("RAY_CLASSIFICATION=WINDOW_AUGMENTATION_ONLY")
    raise SystemExit(72)

emit("RAY_CLASSIFICATION=NO_EXPLICIT_API_TYPE_DECLARATION")
raise SystemExit(73)
