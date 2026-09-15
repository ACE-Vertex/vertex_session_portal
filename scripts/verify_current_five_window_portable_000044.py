from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "current" / "VertexSessionPortal-current-win-x64"
EXE = RELEASE / "Vertex Session Portal.exe"
MANIFEST = RELEASE / "build-manifest.json"
SHA_FILE = RELEASE / "Vertex Session Portal.exe.sha256.txt"

def check(name, value, failures):
    print(f"{name}={'PASS' if value else 'FAIL'}")
    if not value:
        failures.append(name)

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=== VERTEX SESSION PORTAL / CURRENT FIVE-WINDOW PORTABLE VERIFY 000044 ===")
    print(f"ROOT={ROOT}")
    failures = []

    check("PORTABLE_DIR_PRESENT", RELEASE.exists(), failures)
    check("PORTABLE_EXE_PRESENT", EXE.exists(), failures)
    check("BUILD_MANIFEST_PRESENT", MANIFEST.exists(), failures)
    check("PACKAGE_SHA_PRESENT", SHA_FILE.exists(), failures)

    mainframe = ROOT / "src/renderer/src/components/MainFrame/MainFrame.ts"
    scaler = ROOT / "src/renderer/src/components/VeraWindowScaler/VeraWindowScaler.ts"
    browser = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts"

    check("FIVE_WINDOW_HEADER_MOUNT",
          mainframe.exists() and "<vertex-vera-window-scaler></vertex-vera-window-scaler>" in mainframe.read_text(encoding="utf-8"),
          failures)
    check("FIVE_WINDOW_MAX_FIVE",
          scaler.exists() and "const MAX_COUNT = 5" in scaler.read_text(encoding="utf-8"),
          failures)
    check("VERA_05_SOURCE",
          browser.exists() and "'vera-05'" in browser.read_text(encoding="utf-8"),
          failures)

    packaged_out = RELEASE / "resources" / "app" / "out"
    check("PACKAGED_OUT_MAIN", (packaged_out / "main" / "index.js").exists(), failures)
    check("PACKAGED_OUT_RENDERER", (packaged_out / "renderer" / "index.html").exists(), failures)

    better = RELEASE / "resources" / "app" / "node_modules" / "better-sqlite3"
    native_prebuild = better / "prebuilds" / "win32-x64.node"
    native_release = better / "build" / "Release" / "better_sqlite3.node"
    check("PACKAGED_BETTER_SQLITE3", better.exists(), failures)
    check("PACKAGED_BETTER_SQLITE3_NATIVE",
          native_prebuild.exists() or native_release.exists(),
          failures)

    if EXE.exists() and MANIFEST.exists():
        digest = sha256(EXE)
        record = json.loads(MANIFEST.read_text(encoding="utf-8"))
        check("MANIFEST_FIVE_WINDOW_TRUE", record.get("five_window_source_verified") is True, failures)
        check("MANIFEST_MAX_WINDOW_FIVE", record.get("max_window_count") == 5, failures)
        check("MANIFEST_SHA_MATCH", record.get("exe_sha256") == digest, failures)
        check("SHA_FILE_MATCH", digest in SHA_FILE.read_text(encoding="utf-8"), failures)
        print(f"CANONICAL_CURRENT_EXE={EXE}")
        print(f"PORTABLE_EXE_SHA256={digest}")

    if failures:
        print("FAILURES=" + ",".join(failures))
        raise SystemExit(2)

    print("VERTEX_SESSION_PORTAL_CURRENT_FIVE_WINDOW_PORTABLE_VERIFY_000044=PASS")

if __name__ == "__main__":
    main()
