from pathlib import Path
import hashlib
import subprocess

PORTAL = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = PORTAL / "src/main/shell/vertex-shell-service.ts"

EXPECTED_PRE_PATCH_SHA = "5887d1be1857706fb06833b851ab098871c3e459ab8a97e7059b317ff3f0a860"
EXPECTED_POST_PATCH_SHA = "e0bbba6057097005857527953a8470f5dde41cf876ac6a5bb16737d327f66b2e"

failures = []

def ck(name, ok, detail=""):
    print(name + "=" + ("PASS" if ok else "FAIL") + ((" " + detail) if detail else ""))
    if not ok:
        failures.append(name)

ck("SERVICE_PRESENT", SERVICE.is_file())

text = SERVICE.read_text(encoding="utf-8") if SERVICE.is_file() else ""
sha = hashlib.sha256(SERVICE.read_bytes()).hexdigest() if SERVICE.is_file() else ""

ck("POST_PATCH_SHA", sha == EXPECTED_POST_PATCH_SHA, sha)
ck("MARKER", "VXS_CLIPBOARD_NORMALIZATION_000027" in text)
ck("CANONICAL_NORMALIZER", ".replaceAll('VSH │', 'VXS │')" in text)
ck("CLIPBOARD_INSTALLER", "installCanonicalClipboardCopy" in text)
ck("CLIPBOARD_MARKER", "__VXS_CANONICAL_CLIPBOARD_COPY__" in text)
ck("COPY_ONLY", "if (label !== 'COPY') return" in text)
ck("USES_VISIBLE_OUTPUT", "node.textContent || ''" in text)
ck("USES_CANONICAL_TEXT", "normalizeVxsBrandText(" in text)
ck("WRITES_CLIPBOARD", ".writeText(canonicalTranscript)" in text)
ck("REFRESH_INSTALLS_COPY", "installCanonicalClipboardCopy()" in text)
ck("NO_PREVENT_DEFAULT", "preventDefault()" not in text[text.find("const installCanonicalClipboardCopy"):text.find("const installSynchronousOutputBranding")])
ck("NO_STOP_PROPAGATION", "stopPropagation()" not in text[text.find("const installCanonicalClipboardCopy"):text.find("const installSynchronousOutputBranding")])
ck("NO_STOP_IMMEDIATE", "stopImmediatePropagation()" not in text)
ck("EXPLORER_SCOPE_PRESERVED", "COPY PATH" in text)
ck("NO_OBSERVATION_ROUTER_CHANGE", "EvidenceReturnObservabilityTap" not in text)
ck("NO_ACK_PATH_CHANGE", "RETURNED" not in text[text.find("const installCanonicalClipboardCopy"):text.find("const installSynchronousOutputBranding")])

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

print("VXS_CLIPBOARD_NORMALIZATION_000027=PASS")
raise SystemExit(0)
