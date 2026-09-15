from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import tempfile

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage Vertex Workstation headless server into a built Session Portal release."
    )
    parser.add_argument("--workstation-root", type=Path, required=True)
    parser.add_argument("--portal-release-root", type=Path, required=True)
    args = parser.parse_args()

    workstation_root = args.workstation_root.resolve()
    release_root = args.portal_release_root.resolve()

    candidates = [
        workstation_root / "headless" / "target" / "release" / "vertex.exe",
        workstation_root / "headless" / "target" / "debug" / "vertex.exe",
    ]
    source = next((p for p in candidates if p.is_file()), None)
    if source is None:
        raise SystemExit("WORKSTATION_SERVER_BINARY_NOT_FOUND")

    resources = release_root / "resources" / "workstation-server"
    resources.mkdir(parents=True, exist_ok=True)
    destination = resources / "vertex.exe"

    with tempfile.NamedTemporaryFile(
        prefix="vertex-workstation-",
        suffix=".tmp",
        dir=resources,
        delete=False
    ) as tmp:
        temp_path = Path(tmp.name)

    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, destination)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    manifest = {
        "schema": "vertex-session-portal/embedded-workstation-server-1",
        "process_model": "SEPARATE_PROCESS",
        "bind": "127.0.0.1:47832",
        "source": str(source),
        "executable": "vertex.exe",
        "sha256": sha256(destination),
    }
    (resources / "embedded-runtime.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print("WORKSTATION_SERVER_RUNTIME_STAGED=PASS")
    print(f"DESTINATION={destination}")
    print(f"SHA256={manifest['sha256']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
