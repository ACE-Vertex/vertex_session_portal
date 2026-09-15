from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts",
    ROOT / "src" / "main" / "shell" / "vxs" / "vxs-command-registry.ts",
    ROOT / "src" / "main" / "shell" / "vxs" / "vxs-powershell-engine-adapter.ts",
    ROOT / "src" / "main" / "shell" / "vxs" / "vxs-native-organ-provider.ts",
    ROOT / "src" / "main" / "shell" / "vxs" / "vxs-provider-resolver.ts",
]

PATTERNS = [
    re.compile(r"\bexecute\b", re.I),
    re.compile(r"\bresolveBackend\b", re.I),
    re.compile(r"\bspawn\s*\(", re.I),
    re.compile(r"\bVxsCommandRegistry\b"),
    re.compile(r"\bVxsProviderResolver\b"),
    re.compile(r"\bpowerShellFallback\b"),
    re.compile(r"\bregister\b", re.I),
    re.compile(r"\bcommand\b", re.I),
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def collect_hits(path: Path, lines: list[str]) -> list[dict]:
    hits = []
    seen = set()
    for idx, line in enumerate(lines):
        if not any(rx.search(line) for rx in PATTERNS):
            continue
        start = max(0, idx - 4)
        end = min(len(lines), idx + 7)
        key = (start, end)
        if key in seen:
            continue
        seen.add(key)
        hits.append({
            "start_line": start + 1,
            "end_line": end,
            "text": "\n".join(lines[start:end]),
        })
        if len(hits) >= 12:
            break
    return hits

files = []
missing = []

for path in TARGETS:
    rel = path.relative_to(ROOT).as_posix()
    if not path.is_file():
        missing.append(rel)
        continue

    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()

    files.append({
        "path": rel,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "line_count": len(lines),
        "imports": [
            line.strip()
            for line in lines[:120]
            if line.lstrip().startswith("import ")
        ][:30],
        "hits": collect_hits(path, lines),
    })

required = {
    "src/main/shell/vertex-shell-service.ts",
    "src/main/shell/vxs/vxs-command-registry.ts",
    "src/main/shell/vxs/vxs-powershell-engine-adapter.ts",
    "src/main/shell/vxs/vxs-native-organ-provider.ts",
    "src/main/shell/vxs/vxs-provider-resolver.ts",
}

found = {item["path"] for item in files}
not_found_required = sorted(required - found)

result = {
    "schema": "vertex-vxs/normal-route-ray-1",
    "state": "PASS" if not not_found_required else "FAIL",
    "project_root": str(ROOT),
    "files": files,
    "missing": missing,
    "required_missing": not_found_required,
}

print("VXS_NORMAL_ROUTE_RAY=" + json.dumps(result, ensure_ascii=False, separators=(",", ":")))

if not_found_required:
    print("VXS_NORMAL_ROUTE_RAY_RESULT=FAIL")
    print("MISSING=" + ";".join(not_found_required))
    raise SystemExit(20)

print("VXS_NORMAL_ROUTE_RAY_RESULT=PASS")
print("FILE_COUNT=" + str(len(files)))
for item in files:
    print("FILE=" + item["path"])
    print("SHA256=" + item["sha256"])
    print("LINES=" + str(item["line_count"]))

raise SystemExit(0)
