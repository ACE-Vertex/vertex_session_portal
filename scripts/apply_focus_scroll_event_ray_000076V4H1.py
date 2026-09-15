#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
INDEX = ROOT / "src" / "main" / "index.ts"
MODULE = ROOT / "src" / "main" / "diagnostics" / "focus-scroll-event-ray.ts"
EVIDENCE_ROOT = ROOT / "EVIDENCE" / "FOCUS_SCROLL_EVENT_RAY_000076V4H1"
IMPORT_LINE = "import './diagnostics/focus-scroll-event-ray'"
EVENT_RAY_TS = "import { app, webContents, type WebContents } from 'electron'\nimport * as fs from 'node:fs'\nimport * as path from 'node:path'\n\ntype RayRecord = {\n  ts: string\n  mono_ms: number\n  type: string\n  wc_id?: number\n  wc_type?: string\n  partition?: string\n  url?: string\n  title?: string\n  payload?: unknown\n}\n\ntype WcState = {\n  lastHumanInputAt: number\n  lastMutationAt: number\n  lastBottomAt: number\n  lastDistanceBottom: number | null\n}\n\nconst EVENT_RAY_ENABLED = process.env.VERTEX_EVENT_RAY !== '0'\nconst FLUSH_INTERVAL_MS = 250\nconst MAX_QUEUE = 4000\nconst MAX_LOG_BYTES = 25 * 1024 * 1024\nconst HUMAN_OWNER_TTL_MS = 15_000\nconst BACKGROUND_MUTATION_FOCUS_WINDOW_MS = 2_500\nconst BACKLASH_WINDOW_MS = 1_500\nconst BACKLASH_DISTANCE_PX = 48\nconst NEAR_BOTTOM_PX = 8\nconst RECENT_HUMAN_SCROLL_MS = 350\nconst PAGE_PREFIX = '[VERTEX_EVENT_RAY]'\n\nlet started = false\nlet logPath = ''\nlet queue: string[] = []\nlet humanOwner: { wcId: number; at: number; source: string } | null = null\nconst attached = new Set<number>()\nconst stateByWc = new Map<number, WcState>()\n\nfunction monoNow(): number {\n  return Date.now()\n}\n\nfunction stateFor(wcId: number): WcState {\n  let state = stateByWc.get(wcId)\n  if (!state) {\n    state = {\n      lastHumanInputAt: 0,\n      lastMutationAt: 0,\n      lastBottomAt: 0,\n      lastDistanceBottom: null,\n    }\n    stateByWc.set(wcId, state)\n  }\n  return state\n}\n\nfunction safeMeta(wc?: WebContents): Partial<RayRecord> {\n  if (!wc || wc.isDestroyed()) return {}\n  const anyWc = wc as any\n  let partition = ''\n  let url = ''\n  let title = ''\n  let wcType = ''\n  try { partition = String(anyWc.session?.getPartition?.() ?? '') } catch {}\n  try { url = String(anyWc.getURL?.() ?? '') } catch {}\n  try { title = String(anyWc.getTitle?.() ?? '') } catch {}\n  try { wcType = String(anyWc.getType?.() ?? '') } catch {}\n  return { wc_id: wc.id, wc_type: wcType, partition, url, title }\n}\n\nfunction rotateIfNeeded(): void {\n  if (!logPath || !fs.existsSync(logPath)) return\n  try {\n    if (fs.statSync(logPath).size < MAX_LOG_BYTES) return\n    for (let i = 3; i >= 1; i -= 1) {\n      const src = `${logPath}.${i}`\n      const dst = `${logPath}.${i + 1}`\n      if (fs.existsSync(src)) {\n        if (fs.existsSync(dst)) fs.unlinkSync(dst)\n        fs.renameSync(src, dst)\n      }\n    }\n    const first = `${logPath}.1`\n    if (fs.existsSync(first)) fs.unlinkSync(first)\n    fs.renameSync(logPath, first)\n  } catch {}\n}\n\nfunction flush(): void {\n  if (!logPath || queue.length === 0) return\n  const batch = queue.splice(0, queue.length).join('\\n') + '\\n'\n  try {\n    rotateIfNeeded()\n    fs.appendFileSync(logPath, batch, 'utf8')\n  } catch {}\n}\n\nfunction emit(type: string, wc?: WebContents, payload?: unknown): void {\n  if (!EVENT_RAY_ENABLED || !logPath) return\n  const record: RayRecord = {\n    ts: new Date().toISOString(),\n    mono_ms: monoNow(),\n    type,\n    ...safeMeta(wc),\n    ...(payload === undefined ? {} : { payload }),\n  }\n  queue.push(JSON.stringify(record))\n  if (queue.length > MAX_QUEUE) queue.splice(0, queue.length - MAX_QUEUE)\n}\n\nfunction markHumanOwner(wc: WebContents, source: string): void {\n  const at = monoNow()\n  humanOwner = { wcId: wc.id, at, source }\n  stateFor(wc.id).lastHumanInputAt = at\n  emit('human_input_owner', wc, { source })\n}\n\nfunction freshHumanOwner(now: number): typeof humanOwner {\n  if (!humanOwner) return null\n  if (now - humanOwner.at > HUMAN_OWNER_TTL_MS) return null\n  return humanOwner\n}\n\nfunction detectFocusCandidate(wc: WebContents, source: string): void {\n  const now = monoNow()\n  const owner = freshHumanOwner(now)\n  const state = stateFor(wc.id)\n  if (owner && owner.wcId !== wc.id) {\n    emit('focus_authority_violation_candidate', wc, {\n      focus_source: source,\n      human_owner_wc_id: owner.wcId,\n      human_owner_age_ms: now - owner.at,\n      human_owner_source: owner.source,\n      background_mutation_age_ms: state.lastMutationAt > 0 ? now - state.lastMutationAt : null,\n      background_mutation_recent:\n        state.lastMutationAt > 0 &&\n        now - state.lastMutationAt <= BACKGROUND_MUTATION_FOCUS_WINDOW_MS,\n    })\n  }\n}\n\nfunction detectScrollBacklash(wc: WebContents, payload: Record<string, unknown>): void {\n  const state = stateFor(wc.id)\n  const now = monoNow()\n  const rawDistance = payload.distanceBottom\n  if (typeof rawDistance !== 'number' || !Number.isFinite(rawDistance)) return\n\n  state.lastDistanceBottom = rawDistance\n\n  if (rawDistance <= NEAR_BOTTOM_PX) {\n    state.lastBottomAt = now\n    emit('scroll_bottom_reached', wc, payload)\n    return\n  }\n\n  const bottomAge = state.lastBottomAt > 0 ? now - state.lastBottomAt : Number.POSITIVE_INFINITY\n  const inputAge = state.lastHumanInputAt > 0 ? now - state.lastHumanInputAt : Number.POSITIVE_INFINITY\n\n  if (\n    bottomAge <= BACKLASH_WINDOW_MS &&\n    rawDistance >= BACKLASH_DISTANCE_PX &&\n    inputAge > RECENT_HUMAN_SCROLL_MS\n  ) {\n    emit('scroll_backlash_candidate', wc, {\n      ...payload,\n      bottom_age_ms: bottomAge,\n      human_input_age_ms: Number.isFinite(inputAge) ? inputAge : null,\n    })\n  }\n}\n\nfunction handlePageRecord(wc: WebContents, data: unknown): void {\n  if (!data || typeof data !== 'object') return\n  const item = data as Record<string, unknown>\n  const eventType = typeof item.type === 'string' ? item.type : 'page_event'\n  const payload =\n    typeof item.payload === 'object' && item.payload !== null\n      ? item.payload as Record<string, unknown>\n      : {}\n\n  const state = stateFor(wc.id)\n\n  if (\n    eventType === 'pointerdown' ||\n    eventType === 'keydown' ||\n    eventType === 'wheel' ||\n    eventType === 'touchstart'\n  ) {\n    markHumanOwner(wc, `page:${eventType}`)\n  }\n\n  if (eventType === 'mutation') state.lastMutationAt = monoNow()\n  if (eventType === 'focusin') detectFocusCandidate(wc, 'page:focusin')\n  if (eventType === 'scroll') detectScrollBacklash(wc, payload)\n\n  emit(`page:${eventType}`, wc, payload)\n}\n\nconst injectedObserver = String.raw`\n(() => {\n  const FLAG = '__VERTEX_FOCUS_SCROLL_EVENT_RAY_V1__'\n  if (window[FLAG]) return 'already-installed'\n  window[FLAG] = true\n\n  const PREFIX = '[VERTEX_EVENT_RAY]'\n  let mutationTimer = 0\n  let resizeTimer = 0\n  const scrollTimers = new WeakMap()\n\n  const elementMeta = (node) => {\n    if (!node || node === document) return { kind: 'document' }\n    if (node === window) return { kind: 'window' }\n    if (!(node instanceof Element)) return { kind: typeof node }\n    return {\n      kind: 'element',\n      tag: node.tagName || null,\n      id: node.id || null,\n      role: node.getAttribute('role'),\n      testid: node.getAttribute('data-testid'),\n    }\n  }\n\n  const activeMeta = () => elementMeta(document.activeElement)\n\n  const emit = (type, payload = {}) => {\n    try {\n      console.debug(PREFIX + JSON.stringify({\n        type,\n        payload: {\n          ...payload,\n          documentHasFocus: document.hasFocus(),\n          visibilityState: document.visibilityState,\n          activeElement: activeMeta(),\n          perfNow: performance.now(),\n        },\n      }))\n    } catch {}\n  }\n\n  const scrollMetrics = (target) => {\n    let el = null\n    if (target === document || target === window) {\n      el = document.scrollingElement || document.documentElement\n    } else if (target instanceof Element) {\n      el = target\n    } else {\n      el = document.scrollingElement || document.documentElement\n    }\n    if (!el) return null\n\n    const scrollTop = Number(el.scrollTop || 0)\n    const scrollHeight = Number(el.scrollHeight || 0)\n    const clientHeight = Number(el.clientHeight || 0)\n    return {\n      scrollTop,\n      scrollHeight,\n      clientHeight,\n      distanceBottom: Math.max(0, scrollHeight - clientHeight - scrollTop),\n      target: elementMeta(el),\n    }\n  }\n\n  document.addEventListener('focusin', (event) => {\n    emit('focusin', { target: elementMeta(event.target) })\n  }, true)\n\n  document.addEventListener('focusout', (event) => {\n    emit('focusout', { target: elementMeta(event.target) })\n  }, true)\n\n  document.addEventListener('pointerdown', (event) => {\n    emit('pointerdown', { target: elementMeta(event.target), button: event.button })\n  }, true)\n\n  document.addEventListener('touchstart', (event) => {\n    emit('touchstart', { target: elementMeta(event.target) })\n  }, { capture: true, passive: true })\n\n  document.addEventListener('wheel', (event) => {\n    emit('wheel', {\n      target: elementMeta(event.target),\n      deltaX: event.deltaX,\n      deltaY: event.deltaY,\n    })\n  }, { capture: true, passive: true })\n\n  document.addEventListener('keydown', (event) => {\n    emit('keydown', {\n      target: elementMeta(event.target),\n      key: event.key,\n      code: event.code,\n      ctrlKey: event.ctrlKey,\n      altKey: event.altKey,\n      shiftKey: event.shiftKey,\n      metaKey: event.metaKey,\n    })\n  }, true)\n\n  document.addEventListener('scroll', (event) => {\n    const target = event.target === document ? document : event.target\n    const key = target && typeof target === 'object' ? target : document\n    const old = scrollTimers.get(key)\n    if (old) clearTimeout(old)\n    const timer = setTimeout(() => {\n      const metrics = scrollMetrics(target)\n      if (metrics) emit('scroll', metrics)\n    }, 70)\n    scrollTimers.set(key, timer)\n  }, true)\n\n  document.addEventListener('visibilitychange', () => emit('visibilitychange', {}), true)\n\n  const mutationObserver = new MutationObserver((records) => {\n    if (mutationTimer) clearTimeout(mutationTimer)\n    mutationTimer = setTimeout(() => {\n      emit('mutation', {\n        recordCount: records.length,\n        childListCount: records.filter((r) => r.type === 'childList').length,\n        characterDataCount: records.filter((r) => r.type === 'characterData').length,\n        attributeCount: records.filter((r) => r.type === 'attributes').length,\n      })\n    }, 100)\n  })\n\n  const observeMutationRoot = () => {\n    const root = document.body || document.documentElement\n    if (!root) return\n    mutationObserver.observe(root, {\n      subtree: true,\n      childList: true,\n      characterData: true,\n      attributes: true,\n      attributeFilter: ['style', 'class', 'aria-expanded', 'aria-busy'],\n    })\n  }\n\n  if (document.body || document.documentElement) observeMutationRoot()\n  else document.addEventListener('DOMContentLoaded', observeMutationRoot, { once: true })\n\n  const resizeObserver = new ResizeObserver((entries) => {\n    if (resizeTimer) clearTimeout(resizeTimer)\n    resizeTimer = setTimeout(() => {\n      emit('resize', {\n        entryCount: entries.length,\n        viewportWidth: window.innerWidth,\n        viewportHeight: window.innerHeight,\n        documentScrollHeight:\n          (document.scrollingElement || document.documentElement)?.scrollHeight || 0,\n      })\n    }, 100)\n  })\n\n  if (document.documentElement) resizeObserver.observe(document.documentElement)\n  if (document.body) resizeObserver.observe(document.body)\n\n  emit('observer_installed', { hrefOrigin: location.origin, readyState: document.readyState })\n  return 'installed'\n})()\n`\n\nasync function injectPageObserver(wc: WebContents, reason: string): Promise<void> {\n  if (wc.isDestroyed()) return\n  try {\n    const result = await wc.executeJavaScript(injectedObserver, true)\n    emit('page_observer_injection', wc, { reason, result })\n  } catch (error) {\n    emit('page_observer_injection_failed', wc, {\n      reason,\n      error: error instanceof Error ? error.message : String(error),\n    })\n  }\n}\n\nfunction attach(wc: WebContents): void {\n  if (!EVENT_RAY_ENABLED || wc.isDestroyed() || attached.has(wc.id)) return\n\n  const wcAny = wc as any\n  let type = ''\n  try { type = String(wcAny.getType?.() ?? '') } catch {}\n  if (type === 'devTools') return\n\n  attached.add(wc.id)\n  stateFor(wc.id)\n  emit('webcontents_attached', wc)\n\n  wcAny.on('focus', () => {\n    emit('webcontents_focus', wc)\n    detectFocusCandidate(wc, 'webcontents:focus')\n  })\n\n  wcAny.on('blur', () => emit('webcontents_blur', wc))\n\n  wcAny.on('before-input-event', (_event: unknown, input: any) => {\n    if (input?.type === 'keyDown') {\n      markHumanOwner(wc, 'before-input-event:keyDown')\n    }\n  })\n\n  wcAny.on('did-start-loading', () => emit('did_start_loading', wc))\n  wcAny.on('did-stop-loading', () => emit('did_stop_loading', wc))\n\n  wcAny.on('dom-ready', () => {\n    emit('dom_ready', wc)\n    void injectPageObserver(wc, 'dom-ready')\n  })\n\n  wcAny.on('did-finish-load', () => {\n    emit('did_finish_load', wc)\n    void injectPageObserver(wc, 'did-finish-load')\n  })\n\n  wcAny.on('did-navigate', (_event: unknown, url: string) => {\n    emit('did_navigate', wc, { url })\n    void injectPageObserver(wc, 'did-navigate')\n  })\n\n  // Electron changed the console-message event shape across releases.\n  // Accept both historical (event, level, message, ...) and newer\n  // (event, details) contracts without binding the Ray to one Electron minor.\n  wcAny.on('console-message', (...args: any[]) => {\n    let message: unknown = null\n    if (typeof args[2] === 'string') {\n      message = args[2]\n    } else if (args[1] && typeof args[1] === 'object' && typeof args[1].message === 'string') {\n      message = args[1].message\n    }\n\n    if (typeof message !== 'string' || !message.startsWith(PAGE_PREFIX)) return\n    try {\n      handlePageRecord(wc, JSON.parse(message.slice(PAGE_PREFIX.length)))\n    } catch {\n      emit('page_record_parse_failed', wc, { sample: message.slice(0, 300) })\n    }\n  })\n\n  wcAny.once('destroyed', () => {\n    emit('webcontents_destroyed', wc)\n    attached.delete(wc.id)\n    stateByWc.delete(wc.id)\n    if (humanOwner?.wcId === wc.id) humanOwner = null\n  })\n\n  void injectPageObserver(wc, 'attach')\n}\n\nfunction start(): void {\n  if (started || !EVENT_RAY_ENABLED) return\n  started = true\n\n  const logDir = path.join(app.getPath('userData'), 'event-ray')\n  fs.mkdirSync(logDir, { recursive: true })\n  logPath = path.join(logDir, 'focus-scroll-event-ray.jsonl')\n\n  emit('event_ray_started', undefined, {\n    schema: 'vertex-session-portal/focus-scroll-event-ray-1',\n    log_path: logPath,\n    passive_observer: true,\n    content_dom_scrape: false,\n    focus_or_scroll_api_override: false,\n  })\n\n  for (const wc of webContents.getAllWebContents()) attach(wc)\n\n  app.on('web-contents-created', (_event, contents) => attach(contents))\n\n  const timer = setInterval(flush, FLUSH_INTERVAL_MS)\n  timer.unref()\n\n  app.on('before-quit', () => {\n    emit('event_ray_stopping')\n    flush()\n  })\n\n  console.log(`[VERTEX EVENT RAY] focus/scroll observer active: ${logPath}`)\n}\n\nif (EVENT_RAY_ENABLED) {\n  void app.whenReady().then(start)\n}\n"

TSC_ERROR_RE = re.compile(r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.*)$")

def stamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run_typecheck() -> dict:
    p = subprocess.run(
        ["npm.cmd", "run", "typecheck:node"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "exit_code": p.returncode,
        "stdout": p.stdout,
        "stderr": p.stderr,
    }

def diagnostics(run: dict) -> list[dict]:
    out = []
    text = run.get("stdout","") + "\n" + run.get("stderr","")
    for raw in text.splitlines():
        m = TSC_ERROR_RE.match(raw.strip())
        if not m:
            continue
        d = m.groupdict()
        out.append({
            "file": d["file"].replace("/", "\\"),
            "line": int(d["line"]),
            "col": int(d["col"]),
            "code": d["code"],
            "msg": d["msg"],
        })
    return out

def diag_key(d: dict) -> tuple:
    return (
        d["file"].lower(),
        d["line"],
        d["col"],
        d["code"],
        d["msg"],
    )

def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".event-ray.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def restore(index_backup: Path, module_existed: bool, module_backup: Path | None) -> None:
    shutil.copy2(index_backup, INDEX)
    if module_existed:
        assert module_backup is not None
        MODULE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(module_backup, MODULE)
    elif MODULE.exists():
        MODULE.unlink()

def main() -> int:
    print("=== VERTEX SESSION PORTAL / FOCUS SCROLL EVENT RAY APPLY 000076V4H1 ===")
    if not ROOT.exists() or not INDEX.exists():
        print("PROJECT_PREFLIGHT=FAIL")
        return 2

    run_dir = EVIDENCE_ROOT / stamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    # Baseline is captured before any TypeScript production file is added.
    baseline = run_typecheck()
    baseline_diags = diagnostics(baseline)
    (run_dir / "baseline-typecheck.stdout.txt").write_text(baseline["stdout"], encoding="utf-8")
    (run_dir / "baseline-typecheck.stderr.txt").write_text(baseline["stderr"], encoding="utf-8")

    index_before = INDEX.read_text(encoding="utf-8-sig", errors="strict")
    index_hash_before = sha256_path(INDEX)
    index_backup = run_dir / "index.ts.before"
    shutil.copy2(INDEX, index_backup)

    module_existed = MODULE.exists()
    module_backup = None
    if module_existed:
        module_backup = run_dir / "focus-scroll-event-ray.ts.before"
        shutil.copy2(MODULE, module_backup)

    # Write the corrected Electron-version-tolerant observer.
    atomic_write(MODULE, EVENT_RAY_TS)

    # Append, rather than prepend, so unrelated existing TypeScript line numbers
    # remain stable for delta comparison during parallel work.
    current = INDEX.read_text(encoding="utf-8-sig", errors="strict")
    if sha256_path(INDEX) != index_hash_before:
        restore(index_backup, module_existed, module_backup)
        print("CONCURRENT_MAIN_INDEX_CHANGE=FAIL_CLOSED")
        return 4

    if current.count(IMPORT_LINE) > 1:
        restore(index_backup, module_existed, module_backup)
        print("IMPORT_DUPLICATE_PREEXISTING=FAIL")
        return 4

    if IMPORT_LINE not in current:
        patched = current
        if not patched.endswith("\n"):
            patched += "\n"
        patched += "\n// VERTEX_FOCUS_SCROLL_EVENT_RAY_000076V4H1\n" + IMPORT_LINE + "\n"
        atomic_write(INDEX, patched)

    post = run_typecheck()
    post_diags = diagnostics(post)
    (run_dir / "post-typecheck.stdout.txt").write_text(post["stdout"], encoding="utf-8")
    (run_dir / "post-typecheck.stderr.txt").write_text(post["stderr"], encoding="utf-8")

    baseline_keys = {diag_key(x) for x in baseline_diags}
    new_diags = [x for x in post_diags if diag_key(x) not in baseline_keys]
    ray_diags = [
        x for x in post_diags
        if x["file"].lower().endswith("src\\main\\diagnostics\\focus-scroll-event-ray.ts")
    ]

    # Promotion rule:
    # - clean baseline => clean post required.
    # - dirty baseline due parallel work => no NEW diagnostic and no Ray diagnostic.
    if baseline["exit_code"] == 0:
        acceptable = post["exit_code"] == 0 and not post_diags
        mode = "CLEAN_BASELINE_CLEAN_POST_REQUIRED"
    else:
        acceptable = (not new_diags) and (not ray_diags)
        mode = "DIRTY_BASELINE_NO_NEW_DIAGNOSTIC_ALLOWED"

    if not acceptable:
        restore(index_backup, module_existed, module_backup)
        result = {
            "schema":"vertex-session-portal/focus-scroll-event-ray-install/1",
            "status":"TYPECHECK_DELTA_FAILED_ROLLED_BACK",
            "baseline_exit":baseline["exit_code"],
            "post_exit":post["exit_code"],
            "baseline_diagnostics":baseline_diags,
            "post_diagnostics":post_diags,
            "new_diagnostics":new_diags,
            "ray_diagnostics":ray_diags,
            "comparison_mode":mode,
        }
        rp = run_dir / "focus_scroll_event_ray_install_000076V4H1.json"
        rp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
        print("TYPECHECK_DELTA=FAIL")
        print(f"BASELINE_EXIT={baseline['exit_code']}")
        print(f"POST_EXIT={post['exit_code']}")
        print(f"NEW_DIAGNOSTICS={len(new_diags)}")
        for d in new_diags[:20]:
            print("NEW_TSC_ERROR=" + json.dumps(d, ensure_ascii=False))
        print("TRANSACTION_ROLLBACK=PASS")
        print(f"EVIDENCE={rp}")
        return 5

    report = {
        "schema":"vertex-session-portal/focus-scroll-event-ray-install/1",
        "artifact":"vertex-session-portal-focus-scroll-event-ray-000076V4H1",
        "timestamp":dt.datetime.now().isoformat(),
        "status":"INSTALLED",
        "comparison_mode":mode,
        "baseline_exit":baseline["exit_code"],
        "post_exit":post["exit_code"],
        "baseline_diagnostics":baseline_diags,
        "post_diagnostics":post_diags,
        "new_diagnostics":new_diags,
        "ray_diagnostics":ray_diags,
        "index_hash_before":index_hash_before,
        "index_hash_after":sha256_path(INDEX),
        "module_path":str(MODULE),
        "runtime_log":"Electron app.getPath('userData')/event-ray/focus-scroll-event-ray.jsonl",
        "preserved_boundaries":{
            "renderer_layout_mutated":False,
            "VeraBrowserSession_mutated":False,
            "preload_mutated":False,
            "VRA_dispatch_mutated":False,
            "workstation_client_mutated":False,
            "focus_api_overridden":False,
            "scroll_api_overridden":False,
            "page_text_captured":False,
        },
    }
    rp = run_dir / "focus_scroll_event_ray_install_000076V4H1.json"
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")

    print(f"BASELINE_TYPECHECK_EXIT={baseline['exit_code']}")
    print(f"POST_TYPECHECK_EXIT={post['exit_code']}")
    print(f"TYPECHECK_COMPARISON_MODE={mode}")
    print("NEW_TYPESCRIPT_DIAGNOSTICS=0")
    print("RAY_TYPESCRIPT_DIAGNOSTICS=0")
    print("PASSIVE_OBSERVER_ONLY=TRUE")
    print("PAGE_TEXT_CAPTURED=FALSE")
    print("FOCUS_SCROLL_API_OVERRIDE=FALSE")
    print("PARALLEL_WORK_DELTA_GUARD=TRUE")
    print(f"EVIDENCE={rp}")
    print("FOCUS_SCROLL_EVENT_RAY_000076V4H1_APPLY=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
