from pathlib import Path
import hashlib
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = PORTAL / "src/main/shell/vertex-shell-service.ts"
EXPECTED_POST_PATCH_SHA = "f227c2a168fa79b97e8abdc3bc6cf67c4bc8cd957e95b171068f6c7b5f8f899c"

failures = []

def ck(name, ok, detail=""):
    print(name + "=" + ("PASS" if ok else "FAIL") + ((" " + detail) if detail else ""))
    if not ok:
        failures.append(name)

ck("SERVICE_PRESENT", SERVICE.is_file())

text = SERVICE.read_text(encoding="utf-8") if SERVICE.is_file() else ""
sha = hashlib.sha256(SERVICE.read_bytes()).hexdigest() if SERVICE.is_file() else ""

start = text.find("const installCanonicalClipboardCopy")
end = text.find("const installSynchronousOutputBranding")
section = text[start:end] if start >= 0 and end > start else ""

ck("POST_PATCH_SHA", sha == EXPECTED_POST_PATCH_SHA, sha)
ck("MARKER", "VXS_CLIPBOARD_OWNERSHIP_REPAIR_000029" in text)
ck("NORMALIZER_PRESERVED", ".replaceAll('VSH │', 'VXS │')" in text)
ck("COPY_INSTALLER", "installCanonicalClipboardCopy" in text)
ck("COPY_MARKER", "__VXS_CANONICAL_CLIPBOARD_COPY__" in text)
ck("COPY_ONLY", "if (label !== 'COPY') return" in section)
ck("VISIBLE_OUTPUT_SOURCE", "node.textContent || ''" in section)
ck("CANONICAL_TRANSCRIPT", "const canonicalTranscript = normalizeVxsBrandText(" in section)
ck("CAPTURE_PHASE", "          true\n        )" in section)
ck("PREVENT_DEFAULT", "event.preventDefault()" in section)
ck("STOP_IMMEDIATE", "event.stopImmediatePropagation()" in section)
ck("SINGLE_VXS_WRITE", section.count(".writeText(canonicalTranscript)") == 1)
ck("EXPLORER_SCOPE_PRESERVED", "COPY PATH" in section)
ck("REFRESH_INSTALLS_COPY", "installCanonicalClipboardCopy()" in text)

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

cp = subprocess.run(
    ["npm.cmd", "run", "typecheck"],
    cwd=PORTAL,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=180,
)

print("TYPECHECK_EXIT=" + str(cp.returncode))
if cp.stdout:
    print("TYPECHECK_STDOUT_TAIL=" + " | ".join(cp.stdout.splitlines()[-20:]))
if cp.stderr:
    print("TYPECHECK_STDERR_TAIL=" + " | ".join(cp.stderr.splitlines()[-20:]))

if cp.returncode != 0:
    raise SystemExit(cp.returncode)

print("VXS_CLIPBOARD_OWNERSHIP_REPAIR_000029=PASS")
raise SystemExit(0)
