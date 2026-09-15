#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
INDEX = ROOT / "src" / "main" / "index.ts"
MODULE = ROOT / "src" / "main" / "diagnostics" / "focus-scroll-event-ray.ts"
EVIDENCE_ROOT = ROOT / "EVIDENCE" / "FOCUS_SCROLL_EVENT_RAY_000076V4H1"
IMPORT_LINE = "import './diagnostics/focus-scroll-event-ray'"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest_report():
    xs = list(EVIDENCE_ROOT.rglob("focus_scroll_event_ray_install_000076V4H1.json")) if EVIDENCE_ROOT.exists() else []
    return max(xs, key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    checks=[]
    checks.append(ck("MAIN_INDEX_EXISTS",INDEX.exists()))
    checks.append(ck("EVENT_RAY_MODULE_EXISTS",MODULE.exists()))
    if not INDEX.exists() or not MODULE.exists():
        return 3

    idx=INDEX.read_text(encoding="utf-8-sig",errors="replace")
    mod=MODULE.read_text(encoding="utf-8-sig",errors="replace")

    checks.append(ck("IMPORT_EXACTLY_ONCE",idx.count(IMPORT_LINE)==1))
    checks.append(ck("EVENT_RAY_MARKER","VERTEX_FOCUS_SCROLL_EVENT_RAY_000076V4H1" in idx))
    checks.append(ck("FOCUS_CANDIDATE","focus_authority_violation_candidate" in mod))
    checks.append(ck("SCROLL_BACKLASH","scroll_backlash_candidate" in mod))
    checks.append(ck("MUTATION_OBSERVER","MutationObserver" in mod))
    checks.append(ck("RESIZE_OBSERVER","ResizeObserver" in mod))
    checks.append(ck("HUMAN_OWNER","human_input_owner" in mod))
    checks.append(ck("ELECTRON_CONSOLE_MESSAGE_COMPAT","Electron changed the console-message event shape" in mod))
    checks.append(ck("NO_MOUSE_BEFORE_INPUT_ASSUMPTION","mouseDown" not in mod))
    checks.append(ck("NO_PAGE_TEXT_CAPTURE","textContent" not in mod and "innerText" not in mod and "innerHTML" not in mod))
    checks.append(ck("NO_FOCUS_OVERRIDE","HTMLElement.prototype.focus" not in mod and ".prototype.focus =" not in mod))
    checks.append(ck("NO_SCROLL_OVERRIDE","Element.prototype.scrollIntoView" not in mod and "window.scrollTo =" not in mod))
    checks.append(ck("LOG_ROTATION","MAX_LOG_BYTES" in mod and "rotateIfNeeded" in mod))
    checks.append(ck("DISABLE_SWITCH","VERTEX_EVENT_RAY" in mod))

    rp=latest_report()
    checks.append(ck("INSTALL_EVIDENCE_EXISTS",rp is not None))
    if rp:
        d=json.loads(rp.read_text(encoding="utf-8-sig"))
        checks.append(ck("INSTALL_STATUS",d.get("status")=="INSTALLED"))
        checks.append(ck("NO_NEW_TSC_DIAGNOSTICS",len(d.get("new_diagnostics") or [])==0))
        checks.append(ck("NO_RAY_TSC_DIAGNOSTICS",len(d.get("ray_diagnostics") or [])==0))
        p=d.get("preserved_boundaries") or {}
        checks.append(ck("RENDERER_LAYOUT_PRESERVED",p.get("renderer_layout_mutated") is False))
        checks.append(ck("VERA_BROWSER_SESSION_PRESERVED",p.get("VeraBrowserSession_mutated") is False))
        checks.append(ck("PRELOAD_PRESERVED",p.get("preload_mutated") is False))
        checks.append(ck("VRA_DISPATCH_PRESERVED",p.get("VRA_dispatch_mutated") is False))
        checks.append(ck("WORKSTATION_CLIENT_PRESERVED",p.get("workstation_client_mutated") is False))

    ok=all(checks)
    print("FOCUS_SCROLL_EVENT_RAY_000076V4H1_VERIFY=" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
