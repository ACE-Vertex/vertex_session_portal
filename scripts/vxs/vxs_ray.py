from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import sys

SKIP_DIRS = {
    ".git", "node_modules", "target", "dist", "out", "coverage",
    ".vite", "__pycache__", ".venv", "venv", "runtime"
}
TEXT_EXT = {
    ".ts", ".tsx", ".js", ".jsx", ".rs", ".py", ".json", ".toml",
    ".md", ".css", ".html", ".yml", ".yaml", ".ps1", ".cmd", ".txt"
}
MAX_FILES = 5000
MAX_SCAN_BYTES = 2 * 1024 * 1024
MAX_MATCHES = 120

def safe_print(text=""):
    try:
        print(text)
    except UnicodeEncodeError:
        print(str(text).encode("ascii", "backslashreplace").decode("ascii"))

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def iter_files(root):
    count = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = Path(base) / name
            count += 1
            if count > MAX_FILES:
                return
            yield path

def main():
    parser = argparse.ArgumentParser(description="VXS read-only workspace Ray")
    parser.add_argument("--root", required=True)
    parser.add_argument("--pattern", default="")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        safe_print("ERROR: Ray root is not a directory: " + str(root))
        return 2

    files = list(iter_files(root))
    ext_counts = {}
    total_bytes = 0
    for p in files:
        try:
            total_bytes += p.stat().st_size
        except OSError:
            continue
        ext = p.suffix.lower() or "<none>"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    safe_print("VXS RAY")
    safe_print("Root: " + str(root))
    safe_print("Mode: READ_ONLY")
    safe_print("Files observed: " + str(len(files)))
    safe_print("Observed bytes: " + str(total_bytes))
    safe_print("")

    markers = [
        "package.json", "Cargo.toml", "pyproject.toml",
        "requirements.txt", ".git"
    ]
    present = [m for m in markers if (root / m).exists()]
    safe_print("Markers: " + (", ".join(present) if present else "none"))

    top_ext = sorted(ext_counts.items(), key=lambda x: (-x[1], x[0]))[:12]
    safe_print(
        "Extensions: "
        + (", ".join(f"{ext}={count}" for ext, count in top_ext) if top_ext else "none")
    )

    important = []
    for name in ["package.json", "Cargo.toml", "pyproject.toml", "README.md"]:
        p = root / name
        if p.is_file():
            important.append(p)
    if important:
        safe_print("")
        safe_print("Important files:")
        for p in important:
            try:
                safe_print(
                    f"  {p.name} bytes={p.stat().st_size} sha256={sha256(p)}"
                )
            except OSError:
                pass

    pattern = args.pattern.strip()
    if not pattern:
        safe_print("")
        safe_print("Use: vxs ray <pattern> for content anchors.")
        safe_print("VXS RAY RESULT: PASS")
        return 0

    try:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)
    except re.error:
        safe_print("ERROR: invalid pattern")
        return 2

    matches = []
    scanned = 0
    for p in files:
        if p.suffix.lower() not in TEXT_EXT:
            continue
        try:
            size = p.stat().st_size
            if size > MAX_SCAN_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        scanned += 1
        for line_no, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                matches.append((p, line_no, line.strip()))
                if len(matches) >= MAX_MATCHES:
                    break
        if len(matches) >= MAX_MATCHES:
            break

    safe_print("")
    safe_print(f"Pattern: {pattern}")
    safe_print(f"Text files scanned: {scanned}")
    safe_print(f"Matches: {len(matches)}")
    for p, line_no, text in matches:
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = p
        safe_print(f"{rel}:{line_no}: {text}")

    if len(matches) >= MAX_MATCHES:
        safe_print(f"TRUNCATED_AT={MAX_MATCHES}")

    safe_print("VXS RAY RESULT: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
