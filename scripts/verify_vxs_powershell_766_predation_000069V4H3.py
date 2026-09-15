from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "scripts" / "vxs_powershell_766_predation_000069V4H3.ps1"

def run(args):
    return subprocess.run(
        args,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=120,
    )

if not PROBE.is_file():
    print("PREDATION_VERIFY=FAIL")
    print("REASON=PROBE_MISSING")
    print("PROBE=" + str(PROBE))
    raise SystemExit(20)

# Parse gate first. This proves the PowerShell source parses before execution.
parser_code = (
    "$tokens=$null;$errors=$null;"
    "[System.Management.Automation.Language.Parser]::ParseFile("
    + "'" + str(PROBE).replace("'", "''") + "',"
    + "[ref]$tokens,[ref]$errors)|Out-Null;"
    "if($errors.Count -gt 0){"
    "$errors|ForEach-Object{Write-Output $_.Message};"
    "exit 1};exit 0"
)

parsed = run(["pwsh.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", parser_code])
if parsed.returncode != 0:
    print("PREDATION_VERIFY=FAIL")
    print("STAGE=POWERSHELL_PARSE")
    print("EXIT_CODE=" + str(parsed.returncode))
    if parsed.stdout:
        print("STDOUT=" + parsed.stdout[-4000:].replace("\n", "\\n"))
    if parsed.stderr:
        print("STDERR=" + parsed.stderr[-4000:].replace("\n", "\\n"))
    raise SystemExit(33)

proc = run([
    "pwsh.exe",
    "-NoLogo",
    "-NoProfile",
    "-NonInteractive",
    "-File",
    str(PROBE),
])

if proc.returncode != 0:
    print("PREDATION_VERIFY=FAIL")
    print("STAGE=POWERSHELL_RUNTIME")
    print("EXIT_CODE=" + str(proc.returncode))
    if proc.stdout:
        print("STDOUT=" + proc.stdout[-8000:].replace("\n", "\\n"))
    if proc.stderr:
        print("STDERR=" + proc.stderr[-8000:].replace("\n", "\\n"))
    raise SystemExit(40)

dock = None
result = None
for line in proc.stdout.splitlines():
    if line.startswith("VXS_PREDATION_DOCK="):
        dock = json.loads(line.split("=", 1)[1])
    elif line.startswith("VXS_PREDATION_RESULT="):
        result = json.loads(line.split("=", 1)[1])

if not dock or dock.get("state") != "DOCKED":
    print("PREDATION_VERIFY=FAIL")
    print("STAGE=DOCK_EVIDENCE")
    raise SystemExit(41)

if not result or result.get("state") != "PASS":
    print("PREDATION_VERIFY=FAIL")
    print("STAGE=CENSUS_EVIDENCE")
    raise SystemExit(42)

print("PREDATION_VERIFY=PASS")
print("PS_VERSION=" + str(dock.get("ps_version")))
print("COMMAND_COUNT=" + str(result.get("command_count")))
print("MODULE_COUNT=" + str(result.get("module_count")))
print("PROVIDER_COUNT=" + str(result.get("provider_count")))
print("ALIAS_COUNT=" + str(result.get("alias_count")))
print("REPORT_PATH=" + str(result.get("report_path")))
print("REPORT_BYTES=" + str(result.get("report_bytes")))
print("REPORT_SHA256=" + str(result.get("report_sha256")))
raise SystemExit(0)
