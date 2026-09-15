from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OLLAMA = "http://127.0.0.1:11434"

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(
            encoding="utf-8",
            errors="backslashreplace",
        )
    except Exception:
        pass

def run(cmd, env=None, timeout=180):
    print("RUN=" + " ".join(map(str, cmd)))
    proc = subprocess.run(
        [str(x) for x in cmd],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        shell=False,
        timeout=timeout,
    )
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print("=== STDERR ===")
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n")
    print(f"EXIT_CODE={proc.returncode}")
    return proc

def resolve(name, fallback):
    candidate = Path(fallback)
    if candidate.exists():
        return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError(f"{name}_NOT_FOUND")

def ensure_electron(node):
    electron_dir = ROOT / "node_modules" / "electron"
    cli = electron_dir / "cli.js"
    install = electron_dir / "install.js"
    exe = electron_dir / "dist" / "electron.exe"

    if not cli.exists():
        raise RuntimeError("ELECTRON_CLI_NOT_FOUND")

    if not exe.exists():
        result = run([node, install], timeout=240)
        if result.returncode != 0:
            raise RuntimeError("ELECTRON_INSTALL_FAILED")

    if not exe.exists():
        raise RuntimeError("ELECTRON_BINARY_NOT_READY")

    return str(cli)

def tags():
    try:
        with urllib.request.urlopen(
            OLLAMA + "/api/tags",
            timeout=3,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8")
            )
        return [
            (item.get("name") or item.get("model") or "")
            for item in payload.get("models", [])
            if (item.get("name") or item.get("model"))
        ]
    except Exception:
        return []

def find_ollama():
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs"
        / "Ollama"
        / "ollama.exe",
        Path(r"C:\Users\acefr\AppData\Local\Programs\Ollama\ollama.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return shutil.which("ollama.exe") or shutil.which("ollama")

def ensure_ollama():
    models = tags()
    if models:
        print("OLLAMA_READY=YES")
        return models

    exe = find_ollama()
    if not exe:
        raise RuntimeError("OLLAMA_EXE_NOT_FOUND")

    print(f"OLLAMA_EXE={exe}")
    flags = 0
    if os.name == "nt":
        flags = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )

    subprocess.Popen(
        [exe, "serve"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    print("OLLAMA_START=REQUESTED")

    for _ in range(30):
        time.sleep(0.5)
        models = tags()
        if models:
            print("OLLAMA_STARTED=YES")
            return models

    raise RuntimeError("OLLAMA_NOT_READY_OR_NO_MODEL")

def main():
    print("VERTEX SESSION PORTAL / SEARCH VERA RETRIEVAL CORE VERIFY 000018")
    print(f"ROOT={ROOT}")

    npm = resolve(
        "npm.cmd",
        r"C:\Program Files\nodejs\npm.cmd",
    )
    node = resolve(
        "node.exe",
        r"C:\Program Files\nodejs\node.exe",
    )
    electron_cli = ensure_electron(node)

    models = ensure_ollama()
    model = "qwen3:8b" if "qwen3:8b" in models else models[0]

    print("LOCAL_PROVIDER=ollama")
    print(f"LOCAL_MODEL={model}")

    target_doc = (
        ROOT
        / "docs"
        / "ARCHITECTURE"
        / "VIRTUAL_ARD_CORE_000016.md"
    )
    if not target_doc.exists():
        raise RuntimeError(
            "SEARCH_VERA_TARGET_DOCUMENT_MISSING"
        )

    build = run(
        [npm, "run", "build"],
        timeout=180,
    )
    if build.returncode != 0:
        print("BUILD=FAIL")
        print("VERTEX_SESSION_PORTAL_SEARCH_VERA_VERIFY_000018=FAIL")
        return 2

    print("BUILD=PASS")

    env = os.environ.copy()
    env["VERTEX_SEARCH_VERA_PROBE"] = "1"
    env["VERTEX_OLLAMA_MODEL"] = model
    env["VERTEX_OLLAMA_ENDPOINT"] = OLLAMA
    env["ELECTRON_DISABLE_SECURITY_WARNINGS"] = "true"

    runtime = run(
        [node, electron_cli, "."],
        env=env,
        timeout=240,
    )
    if runtime.returncode != 0:
        print("SEARCH_VERA_RUNTIME=FAIL")
        print("VERTEX_SESSION_PORTAL_SEARCH_VERA_VERIFY_000018=FAIL")
        return 3

    expected = [
        "SEARCH_VERA_REAL_LLM=PASS",
        "SEARCH_VERA_PROJECT_RETRIEVAL=PASS",
        "SEARCH_VERA_RETRIEVAL_PERSISTENCE=PASS",
        "SEARCH_VERA_UI=PASS",
        "SEARCH_VERA_SCREENSHOT=PASS",
        "SEARCH_VERA_RETRIEVAL_CORE=PASS",
        "VERTEX_SESSION_PORTAL_SEARCH_VERA_PROBE_000018=PASS",
    ]

    missing = [
        marker
        for marker in expected
        if marker not in runtime.stdout
    ]

    if missing:
        print("MISSING_MARKERS=" + ",".join(missing))
        print("VERTEX_SESSION_PORTAL_SEARCH_VERA_VERIFY_000018=FAIL")
        return 4

    evidence = ROOT / "EVIDENCE" / "SEARCH_VERA_PROBE_000018"
    screenshot = evidence / "search-vera-local-retrieval.png"
    state_json = evidence / "search-vera-probe.json"

    if not screenshot.exists() or screenshot.stat().st_size == 0:
        print("SEARCH_VERA_SCREENSHOT_FILE=FAIL")
        print("VERTEX_SESSION_PORTAL_SEARCH_VERA_VERIFY_000018=FAIL")
        return 5

    if not state_json.exists() or state_json.stat().st_size == 0:
        print("SEARCH_VERA_JSON_FILE=FAIL")
        print("VERTEX_SESSION_PORTAL_SEARCH_VERA_VERIFY_000018=FAIL")
        return 6

    print(f"SEARCH_VERA_SCREENSHOT_EVIDENCE={screenshot}")
    print(f"SEARCH_VERA_JSON_EVIDENCE={state_json}")
    print("SEARCH_VERA_RUNTIME=PASS")
    print("VERTEX_SESSION_PORTAL_SEARCH_VERA_VERIFY_000018=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
