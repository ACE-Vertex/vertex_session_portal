from pathlib import Path
import re
import sys

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
print("=== VERTEX SESSION PORTAL / LIVE DISPATCH ORIGIN + FLICKER RAY 000059V5 ===")
print(f"ROOT={ROOT}")
print("MODE=READ_ONLY_SOURCE_AUDIT")
print("PRODUCTION_MUTATION=NONE")

targets = [
    ROOT / "src/main/vra/vra-dispatch-service.ts",
    ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts",
    ROOT / "src/main/workstation/workstation-client.ts",
    ROOT / "src/shared/contracts.ts",
    ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts",
    ROOT / "src/renderer/src/components/VeraBrowserSession/VeraBrowserSession.ts",
]

existing = [p for p in targets if p.is_file()]
for p in targets:
    print(f"FILE_{p.name.upper().replace('.','_').replace('-','_')}={'PASS' if p.is_file() else 'MISS'}")

if not existing:
    print("NO_TARGET_SOURCE=FAIL")
    sys.exit(1)

terms = [
    "発行元情報",
    "VRA_ORIGIN_UNRESOLVED",
    "origin_vera",
    "origin_session",
    "origin_window",
    "sourceSessionId",
    "sourceWindow",
    "return_channel",
    "project_id",
    "project_name",
    "correlation_id",
    "requested_lane",
    "lane_policy",
    "allocated_lane",
    "FAILED",
    "failed",
    "setInterval",
    "setTimeout",
    "replaceChildren",
    "innerHTML",
    "appendChild",
    "removeChild",
    "remove(",
    "reconcile",
    "render",
    "cardKey",
    "dataset",
    "updatedAt",
    "updated_at",
]

def context(lines, idx, radius=5):
    a=max(0,idx-radius); b=min(len(lines),idx+radius+1)
    return "\n".join(f"{j+1:05d}: {lines[j]}" for j in range(a,b))

all_text = {}
for p in existing:
    try:
        all_text[p] = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        all_text[p] = p.read_text(encoding="utf-8", errors="replace")

print("\n--- EXACT / RELATED ANCHORS ---")
for p,text in all_text.items():
    lines=text.splitlines()
    found=0
    for i,line in enumerate(lines):
        if any(t.lower() in line.lower() for t in terms):
            found += 1
            if found <= 80:
                print(f"\n### {p.relative_to(ROOT)} @ L{i+1}")
                print(context(lines,i,4))
    print(f"\nANCHOR_HITS {p.relative_to(ROOT)} = {found}")

# Classify likely origin gate shape.
service = all_text.get(ROOT / "src/main/vra/vra-dispatch-service.ts", "")
renderer = all_text.get(ROOT / "src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts", "")

def boolhit(pattern, text):
    return bool(re.search(pattern, text, re.I | re.S))

print("\n--- ORIGIN GATE CLASSIFICATION ---")
print("SERVICE_HAS_ORIGIN_VERA=" + ("PASS" if "origin_vera" in service else "FAIL"))
print("SERVICE_HAS_ORIGIN_SESSION=" + ("PASS" if "origin_session" in service else "FAIL"))
print("SERVICE_HAS_ORIGIN_WINDOW=" + ("PASS" if "origin_window" in service else "MISS"))
print("SERVICE_HAS_UNRESOLVED_CODE=" + ("PASS" if "VRA_ORIGIN_UNRESOLVED" in service else "MISS"))

# Detect conjunctions/guards that mention all three in a compact region.
compact = re.sub(r"\s+", " ", service)
triplet_guard = boolhit(r"(origin_vera.{0,220}origin_session.{0,220}origin_window|origin_window.{0,220}origin_session.{0,220}origin_vera)", compact)
print("ORIGIN_TRIPLET_GUARD_NEARBY=" + ("YES" if triplet_guard else "NO"))

# UI may combine fields, masking a missing origin_window.
ui_combo = boolhit(r"origin_session.{0,220}(origin_window|window)|origin_window.{0,220}origin_session", re.sub(r"\s+"," ",renderer))
print("UI_COMBINES_SESSION_WINDOW=" + ("YES" if ui_combo else "NO"))

print("\n--- FLICKER / RECONCILE CLASSIFICATION ---")
for label, pat in [
    ("POLLING_SETINTERVAL", r"setInterval"),
    ("FULL_INNERHTML", r"\.innerHTML\s*="),
    ("REPLACE_CHILDREN", r"replaceChildren\s*\("),
    ("REMOVE_NODE", r"\.remove\s*\("),
    ("APPEND_CHILD", r"appendChild\s*\("),
    ("UPDATED_AT_PRESENT", r"updatedAt|updated_at"),
    ("DATASET_KEY_PRESENT", r"dataset\.[A-Za-z_]*key|cardKey|card_key"),
]:
    print(f"{label}=" + ("YES" if boolhit(pat, renderer) else "NO"))

# Flag suspicious identity key use involving volatile fields.
volatile_key = boolhit(r"(key|cardKey|dataset).{0,180}(updatedAt|updated_at|status|approval|error)", re.sub(r"\s+"," ",renderer))
print("VOLATILE_CARD_IDENTITY_SUSPECT=" + ("YES" if volatile_key else "NO"))

# Rebuild-on-status pattern heuristic.
status_rebuild = boolhit(r"(replaceChildren|innerHTML|remove\(|appendChild).{0,500}(status|failed|approval)", re.sub(r"\s+"," ",renderer))
print("STATUS_REBUILD_SUSPECT=" + ("YES" if status_rebuild else "NO"))

print("\n--- REQUIRED HUMAN-READABLE CONCLUSION INPUT ---")
print("CHECK_A=If ORIGIN_TRIPLET_GUARD_NEARBY=YES while UI_COMBINES_SESSION_WINDOW=YES, missing origin_window can be hidden by UI.")
print("CHECK_B=If volatile card identity or rebuild suspect is YES, live flicker likely comes from remount/rebuild during polling.")
print("CHECK_C=Patch must preserve keyed DOM identity across status/error/approval changes and patch dynamic text/badges only.")
print("CHECK_D=origin_session remains canonical routing identity; do not infer origin from active window after capture.")
print("VERTEX_SESSION_PORTAL_LIVE_DISPATCH_ORIGIN_FLICKER_RAY_000059V5=PASS")
