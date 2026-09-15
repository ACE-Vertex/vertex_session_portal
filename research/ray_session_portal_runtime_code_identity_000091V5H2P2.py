from __future__ import annotations
from pathlib import Path
import json, os, subprocess, hashlib

ROOT=Path(r'G:\Vertex_Project\Development\vertex_session_portal')

def safe(v: object)->str:
    return str(v).encode('ascii',errors='backslashreplace').decode('ascii')
def emit(v: object)->None:
    print(safe(v),flush=True)

def ps(query: str)->str:
    cmd=['powershell.exe','-NoProfile','-Command',query]
    p=subprocess.run(cmd,text=True,capture_output=True,errors='replace',timeout=20,shell=False)
    emit(f'POWERSHELL_EXIT={p.returncode}')
    if p.stderr: emit('POWERSHELL_STDERR='+p.stderr[-4000:])
    return p.stdout

def hash_if(path: Path)->str|None:
    try:
        if not path.is_file(): return None
        h=hashlib.sha256()
        with path.open('rb') as f:
            for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
        return h.hexdigest()
    except Exception:
        return None

def main()->int:
    emit('=== SESSION PORTAL RUNTIME CODE IDENTITY RAY 000091V5H2P2 ===')
    emit('MODE=READ_ONLY')
    emit('ROOT='+str(ROOT))
    src=ROOT/'src/main/vra/vra-dispatch-service.ts'
    built=ROOT/'out/main/index.js'
    emit('SOURCE_PRESENT='+('YES' if src.is_file() else 'NO'))
    emit('BUILT_MAIN_PRESENT='+('YES' if built.is_file() else 'NO'))
    emit('SOURCE_HAS_H2_TAP='+('YES' if src.is_file() and 'EvidenceReturnObservabilityTap' in src.read_text(encoding='utf-8',errors='replace') else 'NO'))
    emit('BUILT_MAIN_HAS_H2_TAP='+('YES' if built.is_file() and 'evidence-return-observability-tap-1' in built.read_text(encoding='utf-8',errors='replace') else 'NO'))
    emit('BUILT_MAIN_SHA256='+str(hash_if(built)))

    query = "$p = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'electron|Vertex.*Session.*Portal|vertex-session-portal' -or $_.CommandLine -match 'vertex_session_portal|vertex-session-portal|Vertex.Session.Portal' }; $p | Select-Object ProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3"
    raw=ps(query).strip()
    emit('PROCESS_JSON_BEGIN')
    emit(raw if raw else '[]')
    emit('PROCESS_JSON_END')
    try:
        data=json.loads(raw) if raw else []
    except Exception:
        emit('PROCESS_JSON_PARSE=FAIL')
        return 41
    if isinstance(data,dict): data=[data]
    candidates=[]
    for item in data:
        exe=str(item.get('ExecutablePath') or '')
        cmd=str(item.get('CommandLine') or '')
        name=str(item.get('Name') or '')
        text=(exe+' '+cmd+' '+name).lower()
        if (('session' in text and 'portal' in text) or 'vertex_session_portal' in text or 'vertex-session-portal' in text):
            candidates.append(item)
    emit(f'PORTAL_PROCESS_CANDIDATES={len(candidates)}')
    for i,item in enumerate(candidates[:12]):
        emit(f'PORTAL_PROCESS_{i}_PID={item.get("ProcessId")}')
        emit(f'PORTAL_PROCESS_{i}_NAME={item.get("Name")}')
        emit(f'PORTAL_PROCESS_{i}_EXE={item.get("ExecutablePath")}')
        emit(f'PORTAL_PROCESS_{i}_CMD={item.get("CommandLine")}')
    if not candidates:
        emit('RUNTIME_IDENTITY=NO_PORTAL_PROCESS_CANDIDATE')
        return 42
    joined=' '.join(str(x.get('ExecutablePath') or '')+' '+str(x.get('CommandLine') or '') for x in candidates).lower()
    if str(ROOT).lower() in joined or str(built).lower() in joined:
        emit('RUNTIME_IDENTITY=SOURCE_TREE_OR_OUT_BUILD')
    elif '.exe' in joined:
        emit('RUNTIME_IDENTITY=PACKAGED_OR_PORTABLE_EXE')
    else:
        emit('RUNTIME_IDENTITY=UNRESOLVED')
    emit('RUNTIME_CODE_IDENTITY_RAY=PASS')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
