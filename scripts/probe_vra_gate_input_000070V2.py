
from pathlib import Path
import re, sys

ROOT = Path.cwd()
SERVICE = ROOT / "src/main/vra/vra-dispatch-service.ts"
IPC = ROOT / "src/main/ipc/register-vra-dispatch-ipc.ts"
VALIDATOR = ROOT / "src/shared/vra-policy-validator.ts"
POLICY = ROOT / "src/shared/system-policy-registry.ts"

# Exit map:
# 0  = all approval roots directly receive manifest/VRA/card object-like input
# 90 = all approval roots are identifier-based but each resolves manifest/card in body
# 91 = mixed: some object-input, some identifier+resolve
# 92 = approval roots are identifier-based and do not visibly resolve manifest/card
# 93 = approval roots are stateful/no useful parameters
# 94 = IPC approval handlers carry object payload while service approval roots are id-based
# 95 = IPC approval handlers are id-based too
# 96 = multiple mixed IPC approval shapes
# 97 = approval roots not found
# 98 = parsing ambiguity
# 45 = validator core missing
# 46 = policy resolver missing
# 47 = source unreadable
#
# Read-only. No production mutation.

def read(p):
    try:
        return p.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return None

service = read(SERVICE)
ipc = read(IPC)
validator = read(VALIDATOR)
policy = read(POLICY)

if service is None or ipc is None:
    sys.exit(47)
if validator is None or "validateVraAgainstActivePolicy" not in validator:
    sys.exit(45)
if policy is None or "resolveActiveSystemPolicy" not in policy:
    sys.exit(46)

# Capture method/function header with params and approximate body.
header_re = re.compile(
    r'(?m)^[ \t]*(?:(?:export|private|public|protected|static|async)\s+)*'
    r'(?:(?:function)\s+)?(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*'
    r'\((?P<params>[^;\n]*)\)\s*(?::[^{\n]+)?\{'
)

def extract_blocks(text):
    blocks = []
    for m in header_re.finditer(text):
        name = m.group("name")
        params = m.group("params")
        brace = text.find("{", m.start(), m.end()+1)
        if brace < 0:
            continue
        depth = 0
        end = None
        i = brace
        in_s = in_d = in_bt = False
        esc = False
        while i < len(text):
            ch = text[i]
            if esc:
                esc = False
                i += 1
                continue
            if ch == "\\" and (in_s or in_d or in_bt):
                esc = True
                i += 1
                continue
            if not in_d and not in_bt and ch == "'":
                in_s = not in_s
            elif not in_s and not in_bt and ch == '"':
                in_d = not in_d
            elif not in_s and not in_d and ch == "`":
                in_bt = not in_bt
            elif not (in_s or in_d or in_bt):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            i += 1
        if end:
            blocks.append((name, params, text[m.start():end]))
    return blocks

blocks = extract_blocks(service)
approval_re = re.compile(r'(approve|approval|humanApply|human_apply)', re.I)
approval = [(n,p,b) for n,p,b in blocks if approval_re.search(n)]

if not approval:
    sys.exit(97)

object_words = ("manifest", "vra", "card", "request", "payload", "input")
id_words = ("id", "cardid", "artifactid", "jobid", "artifact_id", "card_id")
resolve_words = (
    "manifest", "readfile", "readfilesync", "json.parse",
    "loadcard", "getcard", "findcard", "resolve", "artifact"
)

kinds = []
for name, params, body in approval:
    pl = params.lower()
    bl = body.lower()
    has_object = any(w in pl for w in object_words)
    has_id = any(w in pl for w in id_words)
    resolves = any(w in bl for w in resolve_words)

    if has_object:
        kinds.append("object")
    elif has_id and resolves:
        kinds.append("id_resolve")
    elif has_id:
        kinds.append("id_only")
    elif params.strip() == "" or params.strip() in ("_", "_event"):
        kinds.append("stateful")
    else:
        kinds.append("unknown")

unique = set(kinds)

if unique == {"object"}:
    sys.exit(0)
if unique == {"id_resolve"}:
    sys.exit(90)
if unique.issubset({"object","id_resolve"}) and len(unique) > 1:
    sys.exit(91)
if "id_only" in unique and unique.issubset({"id_only","id_resolve"}):
    # inspect IPC approval handler shapes before deciding
    pass
elif "stateful" in unique and unique.issubset({"stateful"}):
    sys.exit(93)
elif "unknown" in unique:
    # fall through to IPC shape classification
    pass

# IPC approval handlers: inspect channel + handler parameter vicinity.
approval_handles = []
for m in re.finditer(
    r"ipcMain\.handle\(\s*['\"]([^'\"]*(?:approve|approval|human[-_]?apply)[^'\"]*)['\"]",
    ipc,
    flags=re.I
):
    start = m.start()
    end = ipc.find("})", start)
    if end < 0:
        end = min(len(ipc), start + 1800)
    approval_handles.append(ipc[start:end])

if not approval_handles:
    if unique.issubset({"id_only","id_resolve"}):
        sys.exit(92)
    sys.exit(98)

ipc_kinds = []
for h in approval_handles:
    low = h.lower()
    has_object = any(w in low for w in ("manifest", "card", "payload", "request"))
    has_id = any(w in low for w in ("cardid", "artifactid", "card_id", "artifact_id"))
    if has_object:
        ipc_kinds.append("object")
    elif has_id:
        ipc_kinds.append("id")
    else:
        ipc_kinds.append("unknown")

iu = set(ipc_kinds)
if "object" in iu and unique.issubset({"id_only","id_resolve","unknown"}):
    if len(iu) == 1:
        sys.exit(94)
    sys.exit(96)
if iu == {"id"}:
    sys.exit(95)
if len(iu) > 1:
    sys.exit(96)

if unique.issubset({"id_only","id_resolve"}):
    sys.exit(92)

sys.exit(98)
