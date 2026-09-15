from __future__ import annotations

import pathlib
import sys

# Windows Workstation verification may inherit cp932 from the parent process.
# Force UTF-8 so diagnostics can never fail because source/log text contains
# U+FFFD or other non-cp932 characters.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

root = pathlib.Path(__file__).resolve().parents[1]
target = root / "src" / "main" / "observability" / "observation-sidecar-compat.ts"

checks = []

def check(name: str, ok: bool) -> None:
    checks.append((name, ok))
    print(f"{name}={'PASS' if ok else 'FAIL'}")

check("COMPAT_FILE_EXISTS", target.is_file())

text = target.read_text(encoding="utf-8") if target.is_file() else ""

required = {
    "SCHEMA_CONSTANT": "vertex-workstation/observation-payload-1",
    "SUPPLEMENT_KIND": "WORKSTATION_OBSERVATION_SIDECAR",
    "PARSE_FUNCTION": "export function parseObservationReference",
    "SUPPLEMENT_FUNCTION": "export function toObservationSupplement",
    "SHA256_VERIFY": "createHash('sha256')",
    "BYTE_VERIFY": "stat.size !== bytes",
    "ARTIFACT_ID_VERIFY": "expectedArtifactId && artifactId !== expectedArtifactId",
    "MISSING_OR_INVALID_FAIL_OPEN": "return null",
}

for name, needle in required.items():
    check(name, needle in text)

forbidden = {
    "NO_SECOND_ROUTER": "ReturnRouter",
    "NO_SECOND_QUEUE": "returnQueue",
    "NO_SECOND_ACK": "acknowledgeEvidenceDelivery",
    "NO_WORKSTATION_CLIENT": "WorkstationClient",
    "NO_DISPATCH_SERVICE_IMPORT": "vra-dispatch-service",
}

for name, needle in forbidden.items():
    check(name, needle not in text)

ok = all(value for _, value in checks)
print("UTF8_STDOUT_GUARD=PASS")
print("OBSERVATION_SIDECAR_COMPAT_000008H3_VERIFY=" + ("PASS" if ok else "FAIL"))
raise SystemExit(0 if ok else 1)
