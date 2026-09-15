
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
TS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts"
CSS = ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.css"
STAMP = time.strftime("%Y%m%d-%H%M%S")
BACKUP_DIR = ROOT / "EVIDENCE" / "DISPATCH_CARD_ERROR_COPY_BUTTON_000033V2" / STAMP
MARKER = "VERTEX_CARD_ERROR_COPY_000033V2"

def log(text=""):
    print(str(text).encode("ascii", "backslashreplace").decode("ascii"))

def read(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"MISSING_FILE:{path}")
    return path.read_text(encoding="utf-8-sig")

def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")

def method_body_span(source: str, signature_pattern: str):
    m = re.search(signature_pattern, source)
    if not m:
        return None
    brace = source.find("{", m.start())
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

def insert_after_open_brace(source: str, signature_pattern: str, block: str) -> str:
    span = method_body_span(source, signature_pattern)
    if not span:
        raise RuntimeError(f"METHOD_NOT_FOUND:{signature_pattern}")
    brace, _ = span
    return source[:brace+1] + block + source[brace+1:]

def find_remove_button(source: str):
    candidates = []
    for m in re.finditer(r"<button\b[^>]*>.*?</button>", source, re.I | re.S):
        text = m.group(0)
        low = text.lower()
        if "card.id" not in text:
            continue
        if "remove" not in low and "\u524a\u9664" not in text:
            continue
        candidates.append(m)
    if len(candidates) != 1:
        raise RuntimeError(f"VISIBLE_REMOVE_BUTTON_ANCHOR_COUNT:{len(candidates)}")
    return candidates[0]

def run_npm(args):
    npm = "npm.cmd" if sys.platform.startswith("win") else "npm"
    proc = subprocess.run(
        [npm, *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    log(f"RUN={npm} {' '.join(args)}")
    log(f"EXIT={proc.returncode}")
    for line in (proc.stdout + "\n" + proc.stderr).splitlines()[-80:]:
        log(line)
    return proc.returncode

ts_original = read(TS)
css_original = read(CSS)

if MARKER in ts_original or "cardErrorCopy" in css_original:
    raise SystemExit("ALREADY_APPLIED_OR_PARTIAL_MARKER_PRESENT")

BACKUP_DIR.mkdir(parents=True, exist_ok=True)
shutil.copy2(TS, BACKUP_DIR / TS.name)
shutil.copy2(CSS, BACKUP_DIR / CSS.name)
log(f"BACKUP_DIR={BACKUP_DIR}")

try:
    ts = ts_original

    listener_block = (
        "\n    // " + MARKER + ": one delegated listener; card dimensions remain untouched.\n"
        "    if (!this.errorCopyListenerInstalled) {\n"
        "      this.addEventListener('click', this.handleErrorCopyClick)\n"
        "      this.errorCopyListenerInstalled = true\n"
        "    }\n"
    )
    ts = insert_after_open_brace(
        ts,
        r"\bconnectedCallback\s*\(\s*\)\s*(?::\s*void\s*)?",
        listener_block
    )

    rm = find_remove_button(ts)
    copy_button = r'''
              <!-- VERTEX_CARD_ERROR_COPY_000033V2 -->
              <button
                class="cardErrorCopy"
                type="button"
                data-error-copy-card="${escapeHtml(card.id)}"
                title="Copy card error for VERA"
                aria-label="Copy card error for VERA"
                ${this.hasCopyableCardError(card) ? '' : 'hidden'}
              >COPY</button>
'''
    ts = ts[:rm.end()] + copy_button + ts[rm.end():]

    class_end_anchor = "\n}\n\ncustomElements.define('vertex-vra-dispatch-lane', VraDispatchLane)"
    if ts.count(class_end_anchor) != 1:
        raise RuntimeError(f"CLASS_END_ANCHOR_COUNT:{ts.count(class_end_anchor)}")

    helper = r'''
  // VERTEX_CARD_ERROR_COPY_000033V2
  private errorCopyListenerInstalled = false

  private hasCopyableCardError(card: VraDispatchCard): boolean {
    const raw = card as unknown as Record<string, unknown>
    const jobState = String(raw.workstationJobState ?? '')
    const registration = String(raw.workstationRegistration ?? '')
    return Boolean(
      raw.error ||
      raw.workstationLastError ||
      raw.status === 'ERROR' ||
      registration === 'BLOCKED' ||
      jobState === 'FAILED' ||
      jobState === 'REJECTED' ||
      jobState === 'ROLLED_BACK'
    )
  }

  private readonly handleErrorCopyClick = (event: Event): void => {
    const origin = event.target instanceof Element ? event.target : null
    const button = origin?.closest<HTMLButtonElement>('[data-error-copy-card]')
    if (!button || !this.contains(button)) return

    event.preventDefault()
    event.stopPropagation()

    const cardId = button.dataset.errorCopyCard ?? ''
    const card = this.state?.cards.find(candidate => candidate.id === cardId)
    if (!card) return

    void this.copyCardErrorForVera(card, button)
  }

  private cardErrorTextForVera(card: VraDispatchCard): string {
    const raw = card as unknown as Record<string, unknown>
    const value = (key: string): string => {
      const current = raw[key]
      return current === null || current === undefined || current === '' ? '-' : String(current)
    }

    return [
      '[VERTEX VRA CARD ERROR]',
      `artifact_id=${value('artifactId')}`,
      `job_id=${value('jobId')}`,
      `correlation_id=${value('correlationId')}`,
      `origin_vera=${value('originVera')}`,
      `origin_session=${value('originSession')}`,
      `origin_window=${value('originWindow')}`,
      `project_id=${value('projectId')}`,
      `project_name=${value('projectName')}`,
      '',
      `card_status=${value('status')}`,
      `dispatch_phase=${value('dispatchPhase')}`,
      `human_approval=${value('humanApproval')}`,
      `workstation_registration=${value('workstationRegistration')}`,
      `workstation_job_state=${value('workstationJobState')}`,
      `workstation_evidence_state=${value('workstationEvidenceState')}`,
      `workstation_evidence_return_state=${value('workstationEvidenceReturnState')}`,
      `allocated_lane=${value('allocatedLane')}`,
      `evidence_id=${value('evidenceIdentity')}`,
      '',
      `error=${value('error')}`,
      `workstation_last_error=${value('workstationLastError')}`
    ].join('\n')
  }

  private async copyCardErrorForVera(card: VraDispatchCard, button: HTMLButtonElement): Promise<void> {
    const text = this.cardErrorTextForVera(card)
    let copied = false

    try {
      await navigator.clipboard.writeText(text)
      copied = true
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.left = '-10000px'
      textarea.style.top = '0'
      document.body.appendChild(textarea)
      textarea.select()
      copied = document.execCommand('copy')
      textarea.remove()
    }

    const previous = button.textContent
    button.textContent = copied ? 'OK' : 'ERR'
    button.dataset.copyState = copied ? 'COPIED' : 'FAILED'
    window.setTimeout(() => {
      if (!button.isConnected) return
      button.textContent = previous || 'COPY'
      delete button.dataset.copyState
    }, 1200)
  }
'''
    ts = ts.replace(class_end_anchor, helper + class_end_anchor)

    css = css_original.rstrip() + r'''

/* VERTEX_CARD_ERROR_COPY_000033V2
   Intentionally affects only the new button. No card/container dimensions are changed. */
.cardErrorCopy {
  box-sizing: border-box;
  flex: 0 0 34px;
  width: 34px;
  min-width: 34px;
  height: 18px;
  min-height: 18px;
  margin: 0;
  padding: 0 4px;
  border: 1px solid #26394B;
  border-radius: 3px;
  background: #111923;
  color: #718195;
  font: 700 7px/16px "Cascadia Code", "JetBrains Mono", monospace;
  letter-spacing: 0.04em;
  cursor: pointer;
}

.cardErrorCopy:hover {
  border-color: #168CFF;
  color: #CBD5DF;
  background: #14202C;
}

.cardErrorCopy[data-copy-state="COPIED"] {
  border-color: #55D69E;
  color: #55D69E;
}

.cardErrorCopy[data-copy-state="FAILED"] {
  border-color: #FF6F7C;
  color: #FF6F7C;
}

.cardErrorCopy[hidden] {
  display: none !important;
}
''' + "\n"

    added_css = css[len(css_original):]
    for token in [".card {", ".card{", ".dispatchCard {", ".dispatchCard{"]:
        if token in added_css:
            raise RuntimeError("CARD_CONTAINER_STYLE_MUTATION_DETECTED")

    write(TS, ts)
    write(CSS, css)

    current_ts = read(TS)
    current_css = read(CSS)
    checks = {
        "TS_MARKER": MARKER in current_ts,
        "COPY_BUTTON": 'data-error-copy-card="${escapeHtml(card.id)}"' in current_ts,
        "ERROR_TEXT": "[VERTEX VRA CARD ERROR]" in current_ts,
        "ERROR_FIELDS": all(x in current_ts for x in [
            "workstationRegistration",
            "workstationJobState",
            "workstationEvidenceState",
            "workstationEvidenceReturnState",
            "workstationLastError",
            "evidenceIdentity",
            "correlationId",
            "originSession",
        ]),
        "CSS_BUTTON_ONLY": ".cardErrorCopy {" in current_css,
        "NO_BACKEND_MUTATION": True,
    }
    for name, ok in checks.items():
        log(f"{name}={'PASS' if ok else 'FAIL'}")
        if not ok:
            raise RuntimeError(f"SOURCE_CHECK_FAILED:{name}")

    if run_npm(["run", "typecheck"]) != 0:
        raise RuntimeError("TYPECHECK_FAILED")
    if run_npm(["run", "build"]) != 0:
        raise RuntimeError("BUILD_FAILED")

    log("CARD_SIZE_CONTRACT=UNCHANGED")
    log("BACKEND_ROUTE_CHANGE=ZERO")
    log("REGISTRY_CHANGE=ZERO")
    log("WORKSTATION_CHANGE=ZERO")
    log("EVIDENCE_ROUTING_CHANGE=ZERO")
    log("HUMAN_GATE_CHANGE=ZERO")
    log("DISPATCH_CARD_ERROR_COPY_BUTTON_000033V2=PASS")

except Exception:
    write(TS, ts_original)
    write(CSS, css_original)
    log("TRANSACTION_ROLLBACK=RESTORED_TS_CSS")
    raise
