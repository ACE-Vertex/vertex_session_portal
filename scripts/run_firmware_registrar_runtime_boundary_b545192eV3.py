from pathlib import Path
import subprocess

ROOT = Path(r"G:\\Vertex_Project\\Development\\vertex_session_portal")
ENTRY = ROOT / "scripts/firmware_registrar_runtime_boundary_b545192eV3.cjs"
ELECTRON = ROOT / "node_modules/.bin/electron.cmd"

print("ENTRY=" + str(ENTRY))
print("ELECTRON=" + str(ELECTRON))
if not ENTRY.exists():
    raise SystemExit(2)
if not ELECTRON.exists():
    raise SystemExit(3)

cp = subprocess.run(
    [str(ELECTRON), str(ENTRY)],
    cwd=ROOT,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=180,
)
print("ELECTRON_EXIT=" + str(cp.returncode))
if cp.stdout:
    print("STDOUT=" + cp.stdout.encode("ascii","backslashreplace").decode("ascii"))
if cp.stderr:
    print("STDERR=" + cp.stderr.encode("ascii","backslashreplace").decode("ascii"))
raise SystemExit(cp.returncode)
