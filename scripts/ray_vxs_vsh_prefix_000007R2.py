from pathlib import Path
import hashlib
import json
import re
import sys

# Windows Workstation redirects Python stdout/stderr to files.
# Force UTF-8 and also escape source-context lines to ASCII-safe text so
# UI glyphs such as gear/cross/box-drawing characters can never crash Ray.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

TARGETS = [
    ROOT / "src" / "main" / "shell" / "vertex-shell-host-bridge.ts",
    ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts",
    ROOT / "src" / "renderer" / "src" / "components" / "VertexShellUnit" / "VertexShellUnit.ts",
    ROOT / "src" / "renderer" / "src" / "components" / "VertexShellUnit" / "VertexShellUnit.css",
]

PATTERNS = [
    ("VSH_PIPE", r"VSH\s*\u2502"),
    ("VSH_PROMPT", r"VSH\s*[\u203a>]"),
    ("VSH_LITERAL", r"\bVSH\b"),
    ("VERTEX_SHELL", r"VERTEX\s+SHELL"),
    ("PREFIX_ASSIGNMENT", r"\bprefix\b"),
    ("APPEND_FN", r"\bappend\b"),
    ("PROMPT_CLASS", r"\.prompt\b"),
    ("OUTPUT_CLASS", r"\.output\b"),
    ("HOST_RECEIVE", r"HOST_RECEIVE|execution_result|message\.type"),
]

def safe(value: object) -> str:
    text = str(value)
    return text.encode("ascii", "backslashreplace").decode("ascii")

def emit(*parts: object) -> None:
    print(" ".join(safe(part) for part in parts))

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def context(lines, index, before=5, after=7):
    start = max(0, index - before)
    end = min(len(lines), index + after + 1)
    for i in range(start, end):
        marker = ">>" if i == index else "  "
        emit(f"{marker} L{i+1:04d}: {lines[i].rstrip()}")
    emit("")

emit("=== VXS VSH PREFIX RAY 000007R2 ===")
emit("ROOT=" + str(ROOT))
emit("MODE=READ_ONLY_SOURCE_INSPECTION")
emit("OUTPUT=UTF8_ASCII_SAFE")
emit("")

missing = []
summary = {}
anchor_contexts = 0

for path in TARGETS:
    rel = str(path.relative_to(ROOT))
    emit("--- FILE", rel, "---")

    if not path.is_file():
        emit("PRESENT=NO")
        emit("")
        missing.append(rel)
        continue

    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()

    emit("PRESENT=YES")
    emit("BYTES=" + str(len(raw)))
    emit("SHA256=" + hashlib.sha256(raw).hexdigest())
    emit("LINES=" + str(len(lines)))

    direct = []
    contextual = []
    seen = set()

    for label, pattern in PATTERNS:
        regex = re.compile(pattern, re.IGNORECASE)
        for idx, line in enumerate(lines):
            if not regex.search(line):
                continue
            key = (idx, label)
            if key in seen:
                continue
            seen.add(key)

            item = {
                "label": label,
                "line": idx + 1,
                "text": line.strip()
            }

            if label in {
                "VSH_PIPE",
                "VSH_PROMPT",
                "VSH_LITERAL",
                "VERTEX_SHELL",
                "PREFIX_ASSIGNMENT"
            }:
                direct.append((idx, item))
            else:
                contextual.append((idx, item))

    summary[rel] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "direct": [item for _, item in direct],
    }

    emit("DIRECT_MATCHES=" + str(len(direct)))

    printed_lines = set()

    for idx, item in direct:
        if idx in printed_lines:
            continue
        printed_lines.add(idx)
        anchor_contexts += 1
        emit(
            "ANCHOR="
            + item["label"]
            + " LINE="
            + str(item["line"])
        )
        context(lines, idx)

    # Emit a few nearby host-rendering anchors if direct literals are sparse.
    if len(printed_lines) < 8:
        for idx, item in contextual:
            if idx in printed_lines:
                continue
            printed_lines.add(idx)
            anchor_contexts += 1
            emit(
                "CONTEXT_ANCHOR="
                + item["label"]
                + " LINE="
                + str(item["line"])
            )
            context(lines, idx, 3, 4)
            if len(printed_lines) >= 12:
                break

    emit("")

emit("=== BROAD SOURCE LEGACY SWEEP ===")
src_root = ROOT / "src"
broad = []

if src_root.is_dir():
    for path in src_root.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in {".ts", ".tsx", ".js", ".jsx", ".css", ".html"}
        ):
            continue

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue

        for idx, line in enumerate(lines, 1):
            if re.search(r"\bVSH\b|VERTEX\s+SHELL", line, re.IGNORECASE):
                broad.append({
                    "file": str(path.relative_to(ROOT)),
                    "line": idx,
                    "text": line.strip(),
                })

for item in broad[:120]:
    emit(
        item["file"]
        + ":"
        + str(item["line"])
        + ": "
        + item["text"]
    )

emit("BROAD_MATCHES=" + str(len(broad)))
emit("")

emit("=== BUILT BUNDLE CHECK ===")
bundle = ROOT / "out" / "main" / "index.js"

if bundle.is_file():
    data = bundle.read_text(encoding="utf-8", errors="replace")
    emit("PRESENT=YES")
    emit("SHA256=" + sha256(bundle))

    literals = [
        "VSH \u2502",
        "VSH \u203a",
        "VSH",
        "VERTEX SHELL 000080V4G",
        "VXS \u2502",
        "VXS_COMMAND",
    ]

    for literal in literals:
        emit(
            "LITERAL="
            + safe(literal)
            + " COUNT="
            + str(data.count(literal))
        )
else:
    emit("PRESENT=NO")

emit("")
emit("=== MACHINE SUMMARY ===")
machine = {
    "target_missing": missing,
    "anchor_contexts": anchor_contexts,
    "broad_matches": len(broad),
    "files": summary,
}
emit(json.dumps(machine, ensure_ascii=True, separators=(",", ":")))
emit("")
emit("PRODUCTION_SOURCE_MUTATION=NONE")
emit("HOST_BRIDGE_MUTATION=NONE")
emit("VERIFY_SIDE_EFFECT=NONE")
emit("READ_ONLY_RAY=PASS")

important_present = TARGETS[0].is_file() and TARGETS[1].is_file()
raise SystemExit(0 if important_present else 2)
