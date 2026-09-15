from pathlib import Path
import hashlib

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
EXPECTED = {'src/main/shell/vertex-shell-service.ts': 'cbb4ab10252772053ac1825ab041c67906681a7625f7447b16c1af80b78cdb3e', 'src/renderer/src/components/VertexShellUnit/VertexShellUnit.ts': '3b11fd3b2b0bdecf84e50d866956449204aec6e70e7465199c9075f895b6a842', 'src/renderer/src/components/VertexShellUnit/VertexShellUnit.css': 'e3c5993d5d8e1058d6830354f92698c03fb9d2131d751838a993f142602eac82'}

print('VXS_CORE_BASELINE_PROBE=START')
mismatch = False
for rel, exp in EXPECTED.items():
    p = ROOT / Path(rel)
    key = rel.replace('/', '_').replace('.', '_').upper()
    if not p.is_file():
        print(key + '_EXISTS=FAIL')
        mismatch = True
        continue
    print(key + '_EXISTS=PASS')
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    print(key + '_SHA256=' + actual)
    print(key + '_EXPECTED=' + exp)
    if actual != exp:
        print(key + '_BASELINE=DIFFERENT')
        mismatch = True
    else:
        print(key + '_BASELINE=EXACT')

print('HOST_BRIDGE_INTENTIONALLY_UNCHECKED=YES')
print('PRODUCTION_MUTATION=NONE')
if mismatch:
    print('VXS_CORE_BASELINE_PROBE=DIFFERENT')
    raise SystemExit(64)
print('VXS_CORE_BASELINE_PROBE=PASS')
raise SystemExit(0)
