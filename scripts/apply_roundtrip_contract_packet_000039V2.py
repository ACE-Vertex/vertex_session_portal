
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

ROOT = Path.cwd()
TARGET = ROOT / "src/renderer/src/components/VeraBrowserSession/VeraEvidenceReturnInjector.ts"
CATALOG = ROOT / "src/shared/vertex-contract-catalog.ts"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP = ROOT / "EVIDENCE" / "ROUNDTRIP_CONTRACT_PACKET_000039V2" / STAMP
OLD_MARKER = "VERTEX_EVIDENCE_CONTRACT_AUTO_INJECTION_000038V2"
NEW_MARKER = "VERTEX_ROUNDTRIP_CONTRACT_PACKET_000039V2"

OLD_BRIDGE = "type VertexContractCatalogBridge = {\n  resolve: (id: 'vertex.evidence.read/1') => Promise<unknown>\n}"
NEW_BRIDGE = "type VertexContractCatalogBridge = {\n  resolve: (id: 'vertex.vra.issue/1' | 'vertex.evidence.read/1') => Promise<unknown>\n}"
VRA_RENDERER = "\n// VERTEX_ROUNDTRIP_CONTRACT_PACKET_000039V2\ntype VertexVraIssueContract = {\n  id?: unknown\n  version?: unknown\n  rules?: unknown\n  example?: unknown\n}\n\nfunction renderVraIssueContract(raw: unknown): string {\n  if (!raw || typeof raw !== 'object') return ''\n  const contract = raw as VertexVraIssueContract\n  if (contract.id !== 'vertex.vra.issue/1') return ''\n\n  const version = typeof contract.version === 'string' ? contract.version : 'active'\n  const rules = Array.isArray(contract.rules)\n    ? contract.rules.filter((item): item is string => typeof item === 'string')\n    : []\n\n  const importantRules = rules.filter(rule =>\n    /schema_version|HUMAN_APPLY|vra-routing|fresh|origin_|return_channel|lane_policy|copy|payload\\/|sha256|verification|TEST|forbidden/i.test(rule)\n  )\n\n  const lines = [\n    `[VERTEX VRA ISSUANCE CONTRACT ${String(contract.id)}@${version}]`,\n    'Use this active contract for the next VRA issuance. Never reconstruct VRA format from LLM memory.'\n  ]\n\n  if (importantRules.length > 0) {\n    lines.push('RULES:')\n    lines.push(...importantRules.map(rule => `- ${rule}`))\n  }\n\n  if (contract.example && typeof contract.example === 'object') {\n    try {\n      lines.push('CANONICAL_EXAMPLE:')\n      lines.push(JSON.stringify(contract.example, null, 2))\n    } catch {\n      // Example rendering is advisory only.\n    }\n  }\n\n  lines.push('[/VERTEX VRA ISSUANCE CONTRACT]')\n  return lines.join('\\\\n')\n}\n"
OLD_BODY = "async function evidencePayloadWithActiveContract(payload: string): Promise<string> {\n  try {\n    const bridge = evidenceContractBridge()\n    if (!bridge) return payload\n    const contract = await bridge.resolve('vertex.evidence.read/1')\n    const rendered = renderEvidenceReadContract(contract)\n    return rendered ? `${rendered}\\n\\n${payload}` : payload\n  } catch {\n    // Fail open for return delivery: contract assistance must never block Evidence.\n    return payload\n  }\n}"
NEW_BODY = "async function evidencePayloadWithActiveContract(payload: string): Promise<string> {\n  try {\n    const bridge = evidenceContractBridge()\n    if (!bridge) return payload\n\n    const [evidenceContract, vraContract] = await Promise.all([\n      bridge.resolve('vertex.evidence.read/1'),\n      bridge.resolve('vertex.vra.issue/1')\n    ])\n\n    const evidenceGuide = renderEvidenceReadContract(evidenceContract)\n    const vraGuide = renderVraIssueContract(vraContract)\n    const contractPacket = [evidenceGuide, vraGuide].filter(Boolean).join('\\n\\n')\n\n    return contractPacket ? `${contractPacket}\\n\\n${payload}` : payload\n  } catch {\n    // Fail open for return delivery: contract assistance must never block Evidence.\n    return payload\n  }\n}"

def log(v=""):
    print(str(v).encode("ascii", "backslashreplace").decode("ascii"))

def read(p: Path) -> str:
    if not p.exists():
        raise RuntimeError(f"MISSING:{p}")
    return p.read_text(encoding="utf-8-sig")

def write(p: Path, s: str):
    p.write_text(s, encoding="utf-8")

def run_npm(args):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    p = subprocess.run(
        [npm, *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    log(f"RUN={npm} {' '.join(args)}")
    log(f"EXIT={p.returncode}")
    for line in (p.stdout + "\n" + p.stderr).splitlines()[-100:]:
        log(line)
    return p.returncode

source0 = read(TARGET)
catalog = read(CATALOG)

if NEW_MARKER in source0:
    raise SystemExit("ALREADY_APPLIED")
if OLD_MARKER not in source0:
    raise SystemExit("BASE_000038V2_NOT_PRESENT")
if "vertex.vra.issue/1" not in catalog or "vertex.evidence.read/1" not in catalog:
    raise SystemExit("CATALOG_CONTRACTS_MISSING")

BACKUP.mkdir(parents=True, exist_ok=True)
shutil.copy2(TARGET, BACKUP / TARGET.name)
log(f"BACKUP={BACKUP / TARGET.name}")

try:
    source = source0

    if source.count(OLD_BRIDGE) != 1:
        raise RuntimeError(f"BRIDGE_ANCHOR_COUNT:{source.count(OLD_BRIDGE)}")
    source = source.replace(OLD_BRIDGE, NEW_BRIDGE, 1)

    insert_anchor = "async function evidencePayloadWithActiveContract(payload: string): Promise<string> {"
    if source.count(insert_anchor) != 1:
        raise RuntimeError(f"EVIDENCE_HELPER_ANCHOR_COUNT:{source.count(insert_anchor)}")
    source = source.replace(insert_anchor, VRA_RENDERER + "\n" + insert_anchor, 1)

    if source.count(OLD_BODY) != 1:
        raise RuntimeError(f"PAYLOAD_HELPER_BODY_COUNT:{source.count(OLD_BODY)}")
    source = source.replace(OLD_BODY, NEW_BODY, 1)

    old_comment = "// VERTEX_EVIDENCE_CONTRACT_AUTO_INJECTION_000038V2: resolve current Evidence interpretation contract before injection."
    new_comment = "// VERTEX_ROUNDTRIP_CONTRACT_PACKET_000039V2: resolve active Evidence-read + next-VRA issuance contracts before injection."
    if old_comment not in source:
        raise RuntimeError("INJECTOR_COMMENT_ANCHOR_MISSING")
    source = source.replace(old_comment, new_comment, 1)

    write(TARGET, source)
    now = read(TARGET)

    checks = {
        "ROUNDTRIP_MARKER": NEW_MARKER in now,
        "EVIDENCE_CONTRACT": "resolve('vertex.evidence.read/1')" in now,
        "VRA_CONTRACT": "resolve('vertex.vra.issue/1')" in now,
        "PARALLEL_RESOLVE": "Promise.all([" in now,
        "VRA_RENDERER": "renderVraIssueContract" in now,
        "CANONICAL_EXAMPLE": "CANONICAL_EXAMPLE:" in now,
        "NO_MEMORY_RULE": "Never reconstruct VRA format from LLM memory." in now,
        "SAME_EVIDENCE_PAYLOAD": "${contractPacket}\\n\\n${payload}" in now,
        "FAIL_OPEN": "contract assistance must never block Evidence" in now,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    if run_npm(["run", "typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run_npm(["run", "build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("NEW_CHAT_MESSAGE_FOR_VRA_POLICY=NO")
    log("CHATGPT_DOM_READ_SCRAPE=ZERO")
    log("EVIDENCE_MESSAGE_SCHEMA_CHANGE=ZERO")
    log("ACK_CONTRACT_CHANGE=ZERO")
    log("REGISTRY_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("RETURN_ROUTER_CHANGE=ZERO")
    log("ROUNDTRIP_CONTRACT_PACKET_000039V2=PASS")

except Exception:
    write(TARGET, source0)
    log("TRANSACTION_ROLLBACK=RESTORED_INJECTOR")
    raise
