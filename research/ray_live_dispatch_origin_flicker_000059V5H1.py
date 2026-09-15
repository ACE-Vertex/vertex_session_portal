from pathlib import Path
import re
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")

# Works/Windows consoles may be CP932. Never let source Unicode abort the Ray.
def safe(s=""):
    text = str(s)
    try:
        enc = sys.stdout.encoding or "cp932"
        return text.encode(enc, errors="backslashreplace").decode(enc, errors="replace")
    except Exception:
        return text.encode("ascii", errors="backslashreplace").decode("ascii")

def p(s=""):
    print(safe(s))

p("=== VERTEX SESSION PORTAL / LIVE DISPATCH ORIGIN + FLICKER RAY 000059V5H1 ===")
p(f"ROOT={ROOT}")
p("MODE=READ_ONLY_SOURCE_AUDIT")
p("PRODUCTION_MUTATION=NONE")
p("CP932_SAFE_OUTPUT=PASS")

targets = {
    "service": ROOT / "src/main/vra/vra-dispatch-service.ts",
    "ipc": ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts",
    "client": ROOT / "src/main/workstation/workstation-client.ts",
    "contracts": ROOT / "src/shared/contracts.ts",
    "lane": ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
    "browser": ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
}

texts = {}
for name, path in targets.items():
    ok = path.is_file()
    p(f"FILE_{name.upper()}={'PASS' if ok else 'MISS'}:{path.relative_to(ROOT) if ok else path}")
    if ok:
        texts[name] = path.read_text(encoding="utf-8", errors="replace")

required = ["service", "client", "lane"]
if any(k not in texts for k in required):
    p("REQUIRED_SOURCE_MISSING=FAIL")
    sys.exit(1)

def lines_of(name):
    return texts[name].splitlines()

def context(name, needle, radius=8, max_hits=8, regex=False):
    lines = lines_of(name)
    hits = []
    pat = re.compile(needle, re.I) if regex else None
    for i, line in enumerate(lines):
        yes = bool(pat.search(line)) if regex else needle.lower() in line.lower()
        if yes:
            hits.append(i)
    p(f"ANCHOR_{name.upper()}_{re.sub(r'[^A-Za-z0-9]+','_',needle)[:40].upper()}_HITS={len(hits)}")
    for idx in hits[:max_hits]:
        a=max(0,idx-radius); b=min(len(lines),idx+radius+1)
        p(f"--- {name}:{idx+1} ---")
        for j in range(a,b):
            p(f"{j+1:05d}: {lines[j]}")

def extract_braced_after(name, anchor, max_chars=50000):
    text=texts[name]
    m=re.search(anchor,text,re.I|re.M)
    if not m:
        return None
    start=m.start()
    brace=text.find("{",m.end())
    if brace<0:
        return text[start:start+2000]
    depth=0; quote=None; esc=False
    for i in range(brace,min(len(text),brace+max_chars)):
        ch=text[i]
        if quote:
            if esc: esc=False
            elif ch=="\\": esc=True
            elif ch==quote: quote=None
            continue
        if ch in ("'",'"','`'):
            quote=ch; continue
        if ch=="{": depth+=1
        elif ch=="}":
            depth-=1
            if depth==0:
                return text[start:i+1]
    return text[start:start+max_chars]

def block(name,label,anchor):
    b=extract_braced_after(name,anchor)
    p(f"BLOCK_{label}={'PASS' if b else 'MISS'}")
    if b:
        # Keep report bounded while preserving exact anchors.
        rows=b.splitlines()
        for row in rows[:120]:
            p(row)
        if len(rows)>120:
            p(f"...BLOCK_TRUNCATED_LINES={len(rows)-120}")

# 1) Capture/origin/routing envelope.
p("\n=== A. CAPTURE ORIGIN / ROUTING ENVELOPE ===")
block("service","CAPTURE_ORIGIN",r"(?:private\s+)?captureOrigin\s*\(")
block("service","CAPTURE_SEED",r"(?:private\s+)?captureSeed\s*\(")
block("service","ENSURE_CAPTURE_ROUTING_ENVELOPE",r"(?:private\s+)?ensureCaptureRoutingEnvelope\s*\(")
block("service","METADATA_FROM_CARD",r"(?:private\s+)?metadataFromCard\s*\(")
block("service","CARD_FOR_RENDERER",r"(?:private\s+)?cardForRenderer\s*\(")

# 2) Workstation registration boundary / error mapping.
p("\n=== B. WORKSTATION REGISTRATION ===")
for needle in [
    "register", "origin_vera", "origin_session", "origin_window",
    "return_channel", "project_id", "project_name", "artifact_sha256",
    "VRA_ORIGIN", "registration"
]:
    context("client",needle,radius=5,max_hits=12)
context("service","reconcileWorkstationCard",radius=8,max_hits=12)
context("service","workstationRegistration",radius=8,max_hits=12)
context("service","humanMessage",radius=8,max_hits=12)

# 3) Renderer live identity / polling / rebuild.
p("\n=== C. DISPATCH CARD LIVE RECONCILE / FLICKER ===")
for needle in [
    "setInterval", "setTimeout", "poll", "reconcile", "render",
    "innerHTML", "replaceChildren", "appendChild", "removeChild", ".remove(",
    "card.id", "dataset", "updatedAt", "updated_at",
    "status", "humanApproval", "dispatchPhase", "error"
]:
    context("lane",needle,radius=5,max_hits=15)

# compact classifier
lane=texts["lane"]
service=texts["service"]
client=texts["client"]
compact_lane=re.sub(r"\s+"," ",lane)
compact_service=re.sub(r"\s+"," ",service)
compact_client=re.sub(r"\s+"," ",client)

def has(text, pat):
    return bool(re.search(pat,text,re.I|re.S))

p("\n=== D. CLASSIFICATION ===")
p("SERVICE_ORIGIN_SESSION_PRESENT=" + ("YES" if "origin_session" in service else "NO"))
p("SERVICE_ORIGIN_WINDOW_PRESENT=" + ("YES" if "origin_window" in service else "NO"))
p("CLIENT_ORIGIN_SESSION_PRESENT=" + ("YES" if "origin_session" in client else "NO"))
p("CLIENT_ORIGIN_WINDOW_PRESENT=" + ("YES" if "origin_window" in client else "NO"))

# A display combining session/window can visually hide one null field.
ui_combined = has(compact_lane, r"origin(Session|_session).{0,240}origin(Window|_window)|origin(Window|_window).{0,240}origin(Session|_session)")
p("UI_SESSION_WINDOW_COMBINED_NEARBY=" + ("YES" if ui_combined else "NO"))

# Detect full-shell rebuild primitives in renderer.
p("LANE_INNERHTML_ASSIGN=" + ("YES" if has(lane,r"\.innerHTML\s*=") else "NO"))
p("LANE_REPLACE_CHILDREN=" + ("YES" if has(lane,r"replaceChildren\s*\(") else "NO"))
p("LANE_APPEND_CHILD=" + ("YES" if has(lane,r"appendChild\s*\(") else "NO"))
p("LANE_REMOVE_NODE=" + ("YES" if has(lane,r"\.remove\s*\(") else "NO"))
p("LANE_POLLING=" + ("YES" if has(lane,r"setInterval|setTimeout|poll") else "NO"))

# Look for a volatile identity/key coupled to changing status/error/time fields.
volatile = has(compact_lane, r"(key|dataset|identity|cardId|card\.id).{0,300}(updatedAt|updated_at|status|error|humanApproval|dispatchPhase)")
p("VOLATILE_CARD_IDENTITY_SUSPECT=" + ("YES" if volatile else "NO"))

# Look for rebuild primitives near state changes.
state_rebuild = has(compact_lane, r"(innerHTML|replaceChildren|appendChild|\.remove\().{0,600}(status|error|humanApproval|dispatchPhase)") or has(compact_lane, r"(status|error|humanApproval|dispatchPhase).{0,600}(innerHTML|replaceChildren|appendChild|\.remove\()")
p("STATE_REBUILD_SUSPECT=" + ("YES" if state_rebuild else "NO"))

# Routing registration completeness heuristic: report exact required fields in client.
for f in ["origin_vera","origin_session","origin_window","return_channel","project_id","project_name","job_id","artifact_id","artifact_sha256"]:
    p(f"CLIENT_FIELD_{f.upper()}=" + ("YES" if f in client else "NO"))

p("\n=== E. NEXT REPAIR CONTRACT ===")
p("REPAIR_RULE_1=Do not infer origin from active/focused/current window after capture.")
p("REPAIR_RULE_2=Use origin_session as canonical return identity; preserve captured origin_window metadata without inventing it.")
p("REPAIR_RULE_3=Portal registration payload and Workstation required-field gate must use the same nullable/required contract.")
p("REPAIR_RULE_4=Dispatch card DOM identity must be keyed by stable card.id/job_id only, never status/error/timestamp.")
p("REPAIR_RULE_5=Polling must patch text/badges/buttons in place; do not remount unchanged card shell.")
p("REPAIR_RULE_6=FAILED state must remain durable and Human retryable without approval loss.")
p("VERTEX_SESSION_PORTAL_LIVE_DISPATCH_ORIGIN_FLICKER_RAY_000059V5H1=PASS")
