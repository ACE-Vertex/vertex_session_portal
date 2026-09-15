
from __future__ import annotations

from pathlib import Path
import re
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
BACKUP = ROOT / "EVIDENCE" / "EVIDENCE_CONTRACT_AUTO_INJECTION_000038V2" / STAMP
MARKER = "VERTEX_EVIDENCE_CONTRACT_AUTO_INJECTION_000038V2"

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

def brace_span(source: str, start: int):
    brace = source.find("{", start)
    if brace < 0:
        return None
    depth = 0
    quote = None
    esc = False
    for i in range(brace, len(source)):
        ch = source[i]
        if quote:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return brace, i
    return None

def detect_payload_field(source: str, fn_body: str):
    type_match = re.search(r"export\s+type\s+VeraEvidenceReturnMessage\s*=\s*\{", source)
    if not type_match:
        raise RuntimeError("MESSAGE_TYPE_NOT_FOUND")
    span = brace_span(source, type_match.start())
    if not span:
        raise RuntimeError("MESSAGE_TYPE_BODY_NOT_FOUND")
    a, b = span
    type_body = source[a+1:b]
    fields = re.findall(r"(?m)^\s*([A-Za-z_$][A-Za-z0-9_$]*)\??\s*:\s*string\b", type_body)
    used = {f for f in fields if re.search(rf"\bmessage\.{re.escape(f)}\b", fn_body)}
    priority = [
        "evidenceText", "evidenceBody", "evidencePayload",
        "messageText", "payload", "content", "body", "text"
    ]
    for name in priority:
        if name in used:
            return name, fields, sorted(used)

    excluded = re.compile(
        r"(?:id|session|origin|channel|path|schema|state|status|time|utc|lane|artifact|job|correlation|project|return)",
        re.I
    )
    candidates = [f for f in used if not excluded.search(f)]
    if len(candidates) == 1:
        return candidates[0], fields, sorted(used)

    raise RuntimeError(
        "PAYLOAD_FIELD_AMBIGUOUS:"
        + ",".join(sorted(used))
        + "|TYPE_FIELDS:"
        + ",".join(fields)
    )

source0 = read(TARGET)
catalog = read(CATALOG)

if MARKER in source0:
    raise SystemExit("ALREADY_APPLIED")
if "vertex.evidence.read/1" not in catalog:
    raise SystemExit("EVIDENCE_CONTRACT_CORE_MISSING")

fn_match = re.search(
    r"export\s+async\s+function\s+injectWorkstationEvidence\s*\(",
    source0
)
if not fn_match:
    raise SystemExit("INJECTOR_FUNCTION_NOT_FOUND")
fn_span = brace_span(source0, fn_match.start())
if not fn_span:
    raise SystemExit("INJECTOR_FUNCTION_BODY_NOT_FOUND")
fn_open, fn_close = fn_span
fn_body0 = source0[fn_open+1:fn_close]

payload_field, type_fields, used_fields = detect_payload_field(source0, fn_body0)
log(f"DETECTED_PAYLOAD_FIELD={payload_field}")
log(f"MESSAGE_STRING_FIELDS={','.join(type_fields)}")
log(f"MESSAGE_USED_STRING_FIELDS={','.join(used_fields)}")

payload_ref = f"message.{payload_field}"
payload_ref_count = len(re.findall(rf"\b{re.escape(payload_ref)}\b", fn_body0))
if payload_ref_count < 1:
    raise SystemExit("PAYLOAD_REFERENCE_NOT_USED")
log(f"PAYLOAD_REFERENCE_COUNT={payload_ref_count}")

BACKUP.mkdir(parents=True, exist_ok=True)
shutil.copy2(TARGET, BACKUP / TARGET.name)
log(f"BACKUP={BACKUP / TARGET.name}")

try:
    helper = r'''
// VERTEX_EVIDENCE_CONTRACT_AUTO_INJECTION_000038V2
type VertexEvidenceReadContract = {
  id?: unknown
  version?: unknown
  rules?: unknown
  stateSemantics?: unknown
  readingOrder?: unknown
}

type VertexContractCatalogBridge = {
  resolve: (id: 'vertex.evidence.read/1') => Promise<unknown>
}

function evidenceContractBridge(): VertexContractCatalogBridge | null {
  return (
    window as unknown as {
      vertexContractCatalog?: VertexContractCatalogBridge
    }
  ).vertexContractCatalog ?? null
}

function renderEvidenceReadContract(raw: unknown): string {
  if (!raw || typeof raw !== 'object') return ''
  const contract = raw as VertexEvidenceReadContract
  if (contract.id !== 'vertex.evidence.read/1') return ''

  const version = typeof contract.version === 'string' ? contract.version : 'active'
  const rules = Array.isArray(contract.rules)
    ? contract.rules.filter((item): item is string => typeof item === 'string')
    : []
  const readingOrder = Array.isArray(contract.readingOrder)
    ? contract.readingOrder.filter((item): item is string => typeof item === 'string')
    : []
  const semantics =
    contract.stateSemantics &&
    typeof contract.stateSemantics === 'object' &&
    !Array.isArray(contract.stateSemantics)
      ? Object.entries(contract.stateSemantics as Record<string, unknown>)
          .filter((entry): entry is [string, string] => typeof entry[1] === 'string')
      : []

  const lines = [
    `[VERTEX EVIDENCE INTERPRETATION CONTRACT ${String(contract.id)}@${version}]`,
    'Use this active contract to interpret the Evidence below. Do not reconstruct Evidence semantics from LLM memory.'
  ]

  if (readingOrder.length > 0) {
    lines.push('READING_ORDER:')
    lines.push(...readingOrder.map(item => `- ${item}`))
  }

  const importantSemantics = semantics.filter(([key]) =>
    /AVAILABLE|RETURN_QUEUED|RETURNED|verified|final_state|rollback|write_lock/i.test(key)
  )
  if (importantSemantics.length > 0) {
    lines.push('STATE_SEMANTICS:')
    lines.push(...importantSemantics.map(([key, value]) => `- ${key} => ${value}`))
  }

  const importantRules = rules.filter(rule =>
    /identity|return|visibility|rollback|boundary|AVAILABLE|Workstation/i.test(rule)
  )
  if (importantRules.length > 0) {
    lines.push('RULES:')
    lines.push(...importantRules.map(rule => `- ${rule}`))
  }

  lines.push('[/VERTEX EVIDENCE INTERPRETATION CONTRACT]')
  return lines.join('\n')
}

async function evidencePayloadWithActiveContract(payload: string): Promise<string> {
  try {
    const bridge = evidenceContractBridge()
    if (!bridge) return payload
    const contract = await bridge.resolve('vertex.evidence.read/1')
    const rendered = renderEvidenceReadContract(contract)
    return rendered ? `${rendered}\n\n${payload}` : payload
  } catch {
    // Fail open for return delivery: contract assistance must never block Evidence.
    return payload
  }
}
'''

    insert_at = fn_match.start()
    source = source0[:insert_at] + helper + "\n" + source0[insert_at:]

    fn_match2 = re.search(
        r"export\s+async\s+function\s+injectWorkstationEvidence\s*\(",
        source
    )
    if not fn_match2:
        raise RuntimeError("INJECTOR_FUNCTION_LOST_AFTER_HELPER_INSERT")
    fn_span2 = brace_span(source, fn_match2.start())
    if not fn_span2:
        raise RuntimeError("INJECTOR_FUNCTION_BODY_LOST_AFTER_HELPER_INSERT")
    open2, close2 = fn_span2
    body = source[open2+1:close2]

    payload_var = "__vertexEvidencePayload"
    body_replaced, replaced_count = re.subn(
        rf"\bmessage\.{re.escape(payload_field)}\b",
        payload_var,
        body
    )
    if replaced_count < 1:
        raise RuntimeError("PAYLOAD_REPLACEMENT_COUNT_ZERO")

    prelude = (
        f"\n  // {MARKER}: resolve current Evidence interpretation contract before injection.\n"
        f"  const {payload_var} = await evidencePayloadWithActiveContract(message.{payload_field})\n"
    )
    body_new = prelude + body_replaced
    source = source[:open2+1] + body_new + source[close2:]

    write(TARGET, source)

    now = read(TARGET)
    checks = {
        "MARKER": MARKER in now,
        "CATALOG_BRIDGE": "vertexContractCatalog" in now,
        "ACTIVE_CONTRACT_RESOLVE": "resolve('vertex.evidence.read/1')" in now,
        "COMPACT_CONTRACT_RENDER": "[VERTEX EVIDENCE INTERPRETATION CONTRACT" in now,
        "RETURN_QUEUED_SEMANTICS_FILTER": "RETURN_QUEUED" in now,
        "DELIVERY_FAIL_OPEN": "contract assistance must never block Evidence" in now,
        "ORIGINAL_MESSAGE_TYPE_PRESERVED": "export type VeraEvidenceReturnMessage" in now,
        "ORIGINAL_INJECTOR_PRESERVED": "export async function injectWorkstationEvidence" in now,
        "PAYLOAD_VAR_PRESENT": payload_var in now,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"CHECK_FAILED:{name}")

    if run_npm(["run", "typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run_npm(["run", "build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("EVIDENCE_MESSAGE_SCHEMA_CHANGE=ZERO")
    log("ACK_CONTRACT_CHANGE=ZERO")
    log("REGISTRY_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("RETURN_ROUTER_CHANGE=ZERO")
    log("CONTRACT_FETCH_FAILURE_BLOCKS_EVIDENCE=NO")
    log("EVIDENCE_CONTRACT_AUTO_INJECTION_000038V2=PASS")

except Exception:
    write(TARGET, source0)
    log("TRANSACTION_ROLLBACK=RESTORED_INJECTOR")
    raise
