from pathlib import Path
import base64, shutil, subprocess, sys, traceback

ROOT = Path(__file__).resolve().parents[1]

def safe(value):
    text = str(value)
    return text.encode("ascii", "backslashreplace").decode("ascii")

def emit(value=""):
    print(safe(value), flush=True)

def die(code, name, detail=""):
    emit(f"FAIL_STAGE={name}")
    if detail:
        emit(f"FAIL_DETAIL={detail}")
    raise SystemExit(code)

def check(name, condition, code):
    emit(f"{name}={'PASS' if condition else 'FAIL'}")
    if not condition:
        die(code, name)

def run(label, command, fail_code):
    emit(f"RUN_{label}={' '.join(map(str, command))}")
    try:
        p = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            encoding='utf-8',
            errors='replace'
        )
    except Exception as exc:
        die(90, f"{label}_LAUNCH_EXCEPTION", f"{type(exc).__name__}:{exc}")
    emit(f"{label}_EXIT={p.returncode}")
    stdout = (p.stdout or '').replace('\r','')
    stderr = (p.stderr or '').replace('\r','')
    if stdout:
        emit(f"{label}_STDOUT=" + ' | '.join(stdout.splitlines()[-40:]))
    if stderr:
        emit(f"{label}_STDERR=" + ' | '.join(stderr.splitlines()[-40:]))
    if p.returncode != 0:
        die(fail_code, label, f"child_exit={p.returncode}")
    return p

def main():
    emit('=== VXS POWERSHELL ENGINE PROVIDER 000067V3H3 VERIFY ===')
    emit(f"PYTHON={sys.executable}")
    emit(f"ROOT={ROOT}")
    emit(f"STDOUT_ENCODING={getattr(sys.stdout, 'encoding', None)}")

    registry = (ROOT/'src/main/shell/vxs/vxs-command-registry.ts').read_text(encoding='utf-8')
    adapter = (ROOT/'src/main/shell/vxs/vxs-powershell-engine-adapter.ts').read_text(encoding='utf-8')
    caps = (ROOT/'src/main/shell/vxs/vxs-powershell-capabilities.ts').read_text(encoding='utf-8')

    check('REGISTRY_IMPORT', "createVxsPowerShellCommands" in registry, 11)
    check('REGISTRY_ROUTE', "...createVxsPowerShellCommands()," in registry, 12)
    check('HELP_SURFACE', "vxs ps engine" in registry and "vxs ps invoke" in registry, 13)
    check('ENGINE_SCHEMA', "vxs-powershell-engine/1" in adapter, 14)
    check('AUTOMATION_ENGINE', 'System.Management.Automation' in adapter, 15)
    check('AST_PARSER', 'Language.Parser' in adapter, 16)
    check('COMMAND_METADATA', 'CommandMetadata' in adapter, 17)
    check('PROVIDER_DISCOVERY', 'Get-PSProvider' in adapter and 'Get-PSDrive' in adapter, 18)
    check('MUTATION_HUMAN_GATE', "HUMAN_APPLY" in adapter and "BLOCKED_HUMAN_APPLY" in adapter, 19)
    check('SAFE_READ_ONLY_INVOKE', "SAFE_READ" in adapter and "executed=$true" in adapter, 20)
    check('CAPABILITY_ALIASES', "aliases: ['ps', 'pwsh']" in caps, 21)

    pwsh = shutil.which('pwsh.exe') or shutil.which('pwsh')
    check('PWSH_AVAILABLE', bool(pwsh), 31)
    emit(f"PWSH={pwsh}")

    probe = (
        "$ErrorActionPreference='Stop';"
        "$e=$null;$t=$null;"
        "$a=[System.Management.Automation.Language.Parser]::ParseInput("
        "'Get-Process | Select-Object -First 1',[ref]$t,[ref]$e);"
        "$c=Get-Command Get-Process -ErrorAction Stop;"
        "$m=[System.Management.Automation.CommandMetadata]::new($c);"
        "if(@($e).Count -ne 0){exit 131};"
        "if($null -eq $a){exit 132};"
        "if($null -eq $m){exit 133};"
        "Write-Output ('PS='+$PSVersionTable.PSVersion.ToString());"
        "Write-Output ('SMA='+[System.Management.Automation.PSObject].Assembly.GetName().Version.ToString());"
        "Write-Output ('CMD='+$c.Name);"
        "Write-Output ('SHOULDPROCESS='+$m.SupportsShouldProcess)"
    )
    encoded = base64.b64encode(probe.encode('utf-16le')).decode('ascii')
    run(
        'POWERSHELL_ENGINE_PROBE',
        [pwsh, '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
        32
    )

    npm = shutil.which('npm.cmd') or shutil.which('npm')
    check('NPM_AVAILABLE', bool(npm), 41)
    emit(f"NPM={npm}")

    run('TYPECHECK', [npm, 'run', 'typecheck'], 42)
    run('BUILD', [npm, 'run', 'build'], 43)

    out_main = ROOT/'out/main/index.js'
    check('BUILD_MAIN_EXISTS', out_main.exists(), 51)
    compiled = out_main.read_text(encoding='utf-8', errors='replace') if out_main.exists() else ''
    check('COMPILED_ENGINE_SCHEMA', 'vxs-powershell-engine/1' in compiled, 52)
    check('COMPILED_ENGINE_ROUTE', 'VXS PowerShell Engine Provider' in compiled, 53)

    emit('FAIL_STAGE=NONE')
    emit('VXS_POWERSHELL_ENGINE_PROVIDER_000067V3H3=VERIFIED')

if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        emit('FAIL_STAGE=VERIFIER_UNHANDLED_EXCEPTION')
        emit(f"FAIL_DETAIL={type(exc).__name__}:{exc}")
        for line in traceback.format_exc().splitlines():
            emit(line)
        raise SystemExit(90)
