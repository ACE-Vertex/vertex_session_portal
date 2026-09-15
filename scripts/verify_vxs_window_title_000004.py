from pathlib import Path

ROOT = Path(r"G:\Vertex_Project\Development\vertex_session_portal")
SERVICE = ROOT / "src" / "main" / "shell" / "vertex-shell-service.ts"

failures = []

def check(name, ok):
    print(name + "=" + ("PASS" if ok else "FAIL"))
    if not ok:
        failures.append(name)

check("SERVICE_PRESENT", SERVICE.is_file())

if SERVICE.is_file():
    text = SERVICE.read_text(encoding="utf-8")
    check("WINDOW_TITLE_EXPANDED", "brand.textContent = 'Vertex eXecution Shell'" in text)
    check("NATIVE_WINDOW_TITLE", "window.setTitle('Vertex eXecution Shell')" in text)
    check("PROMPT_REMAINS_VXS", "prompt.textContent.replace('VSH', 'VXS')" in text)
    check("PREFIX_REMAINS_VXS", "replaceAll('VSH │ ', 'VXS │ ')" in text)
    check("VXS_VERSION_PRESERVED", "VXS_VERSION = '0.1.0'" in text)
    check("VXS_META_PRESERVED", "backend: 'VXS_META'" in text)

print("HOST_BRIDGE_OPERATION=NONE")
print("WORKSTATION_CHANGE=NONE")
print("HUMAN_GATE_CHANGE=NONE")
print("VERIFY_PRODUCTION_MUTATION=NONE")

if failures:
    print("FAILURES=" + ",".join(failures))
    raise SystemExit(1)

print("VXS_WINDOW_TITLE_000004=PASS")
raise SystemExit(0)
