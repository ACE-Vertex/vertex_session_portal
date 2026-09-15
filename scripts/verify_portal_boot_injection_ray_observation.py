from __future__ import annotations

from pathlib import Path
import json
import re
import sys

ROOT = Path.cwd().resolve()

EXCLUDED = {
    ".git", "node_modules", "dist", "build", "out", "coverage",
    ".next", ".vite", "target", "__pycache__", "runtime"
}
EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".md", ".py", ".html"}

TERMS = [
    "webContents", "WebContentsView", "BrowserWindow", "BrowserView",
    "executeJavaScript", "ipcMain", "ipcRenderer", "sendInputEvent",
    "source_web_contents_id", "webContentsId", "origin_session",
    "origin_window", "return-queue", "vertex-session-portal:return-queue",
    "dispatch", "sendMessage", "send_message", "chat", "textarea",
    "contenteditable", "vera-01", "VERA01"
]

secret_rx = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|(?i:(?:api[_-]?key|password|passwd|secret)\s*[:=]\s*)[^\s,;]+)"
)

def redact(s: str) -> str:
    return secret_rx.sub("[REDACTED]", s)

def wanted(path: Path) -> bool:
    try:
        rel = path.relative_to(ROOT)
    except Exception:
        return False
    if any(part in EXCLUDED for part in rel.parts):
        return False
    return path.is_file() and path.suffix.lower() in EXTS

anchors = []
scanned = 0
matched_files = set()

for path in ROOT.rglob("*"):
    if not wanted(path):
        continue
    scanned += 1
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    lines = text.splitlines()
    file_hits = []
    for idx, line in enumerate(lines, 1):
        hits = [t for t in TERMS if t.lower() in line.lower()]
        if not hits:
            continue
        cleaned = redact(line.strip())
        if len(cleaned) > 220:
            cleaned = cleaned[:217] + "..."
        file_hits.append({
            "line": idx,
            "terms": hits[:6],
            "text": cleaned
        })

    if file_hits:
        matched_files.add(str(path.relative_to(ROOT)).replace("\\", "/"))
        anchors.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "hits": len(file_hits),
            "samples": file_hits[:4]
        })

anchors.sort(key=lambda x: (-x["hits"], x["path"]))
anchors = anchors[:24]

report = {
    "schema": "vertex-session-portal/boot-injection-ray-observation-1",
    "summary": {
        "target_root": str(ROOT),
        "mode": "READ_ONLY_SOURCE_OBSERVATION",
        "files_scanned": scanned,
        "matched_files": len(matched_files),
        "anchor_count": len(anchors),
        "purpose": "Locate the existing Session Portal chat transport/control path for a minimal invisible VERA boot firmware injection."
    },
    "likely_integration_anchors": anchors,
    "safety": {
        "source_mutation": False,
        "network_access": False,
        "process_control": False,
        "secret_redaction": True,
        "bounded_output": True
    },
    "next_step": "Use these exact existing transport anchors to design a minimal background BOOT control message before Human chat is enabled; preserve normal LLM personality and inject only Session Portal operating essentials (Ray/VRA/Human Gate/Workstation/Evidence return)."
}

print("=== VERTEX OBSERVATION BOUNDARY AUDIT H2 ===")
print(json.dumps(report, ensure_ascii=False, indent=2))
print("=== VERTEX OBSERVATION BOUNDARY AUDIT H2 COMPLETE ===")
sys.exit(0)
