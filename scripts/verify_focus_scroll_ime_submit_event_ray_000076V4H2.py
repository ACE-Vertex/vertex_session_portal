#!/usr/bin/env python3
from pathlib import Path
import json

ROOT=Path(r"G:\Vertex_Project\Development\vertex_session_portal")
INDEX=ROOT/"src"/"main"/"index.ts"
MODULE=ROOT/"src"/"main"/"diagnostics"/"focus-scroll-event-ray.ts"
EVIDENCE_ROOT=ROOT/"EVIDENCE"/"FOCUS_SCROLL_IME_SUBMIT_EVENT_RAY_000076V4H2"
IMPORT_LINE="import './diagnostics/focus-scroll-event-ray'"

def ck(k,v):
    print(f"{k}={'PASS' if v else 'FAIL'}")
    return bool(v)

def latest():
    xs=list(EVIDENCE_ROOT.rglob("focus_scroll_ime_submit_event_ray_000076V4H2.json")) if EVIDENCE_ROOT.exists() else []
    return max(xs,key=lambda p:p.stat().st_mtime_ns) if xs else None

def main():
    checks=[]
    checks.append(ck("INDEX_EXISTS",INDEX.exists()))
    checks.append(ck("MODULE_EXISTS",MODULE.exists()))
    if not INDEX.exists() or not MODULE.exists():
        return 3

    idx=INDEX.read_text(encoding="utf-8-sig",errors="replace")
    mod=MODULE.read_text(encoding="utf-8-sig",errors="replace")

    checks.append(ck("IMPORT_EXACTLY_ONCE",idx.count(IMPORT_LINE)==1))
    checks.append(ck("COMPOSITION_START","compositionstart" in mod))
    checks.append(ck("COMPOSITION_UPDATE","compositionupdate" in mod))
    checks.append(ck("COMPOSITION_END","compositionend" in mod))
    checks.append(ck("BEFOREINPUT","beforeinput" in mod))
    checks.append(ck("INPUT_EVENT","document.addEventListener('input'" in mod))
    checks.append(ck("SUBMIT_EVENT","document.addEventListener('submit'" in mod))
    checks.append(ck("BUTTON_CLICK_EVENT","button_click" in mod))
    checks.append(ck("IME_ENTER_CANDIDATE","ime_enter_during_composition" in mod))
    checks.append(ck("IME_FOCUS_LOSS_CANDIDATE","ime_composition_focus_loss_candidate" in mod))
    checks.append(ck("IME_SUBMIT_COLLISION_CANDIDATE","ime_submit_collision_candidate" in mod))
    checks.append(ck("SANITIZED_KEY_CLASS","keyClass: classifyKey(event)" in mod))
    checks.append(ck("NO_ACTUAL_KEY_LOG","key: event.key" not in mod))
    checks.append(ck("NO_ACTUAL_CODE_LOG","code: event.code" not in mod))
    checks.append(ck("NO_COMPOSITION_TEXT_LOG","data: event.data" not in mod))
    checks.append(ck("NO_PAGE_TEXT_CAPTURE","textContent" not in mod and "innerText" not in mod and "innerHTML" not in mod))
    checks.append(ck("NO_FOCUS_OVERRIDE","HTMLElement.prototype.focus" not in mod and ".prototype.focus =" not in mod))
    checks.append(ck("NO_SCROLL_OVERRIDE","Element.prototype.scrollIntoView" not in mod and "window.scrollTo =" not in mod))

    rp=latest()
    checks.append(ck("INSTALL_EVIDENCE_EXISTS",rp is not None))
    if rp:
        d=json.loads(rp.read_text(encoding="utf-8-sig"))
        checks.append(ck("INSTALL_STATUS",d.get("status")=="INSTALLED"))
        checks.append(ck("NO_NEW_TSC_DIAGNOSTICS",len(d.get("new_diagnostics") or [])==0))
        checks.append(ck("NO_RAY_TSC_DIAGNOSTICS",len(d.get("ray_diagnostics") or [])==0))
        privacy=d.get("privacy") or {}
        checks.append(ck("ACTUAL_KEY_NOT_LOGGED",privacy.get("actual_key_text_logged") is False))
        checks.append(ck("COMPOSITION_TEXT_NOT_LOGGED",privacy.get("composition_text_logged") is False))
        checks.append(ck("INPUT_VALUE_NOT_LOGGED",privacy.get("input_value_logged") is False))
        checks.append(ck("BEHAVIOR_NOT_MUTATED",d.get("behavior_mutation") is False))
        checks.append(ck("SEND_HANDLER_NOT_MUTATED",d.get("send_handler_mutated") is False))
        checks.append(ck("IME_HANDLER_NOT_MUTATED",d.get("ime_handler_mutated") is False))

    ok=all(checks)
    print("FOCUS_SCROLL_IME_SUBMIT_EVENT_RAY_000076V4H2_VERIFY="+("PASS" if ok else "FAIL"))
    return 0 if ok else 4

if __name__=="__main__":
    raise SystemExit(main())
