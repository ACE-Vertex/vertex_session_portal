from __future__ import annotations
import json, os, sys, urllib.error, urllib.request
from pathlib import Path
from typing import Any
JOB_ID='job-vera05-test-card-redispatch-roundtrip-770e76a6-a4e4-482e-8f57-96779ca0b5f9'
ARTIFACT_ID='vertex-session-portal-test-card-redispatch-roundtrip-smoke-000121V5'
PORTAL_ROOT=Path(r'G:\\Vertex_Project\\Development\\vertex_session_portal')
WORKSTATION_BASE='http://127.0.0.1:47832'
def emit(k,v):
    print(f'{k}='+ (json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else str(v)))
def load_json(path):
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data,dict) else None
    except Exception:
        return None
def http_json(url):
    try:
        with urllib.request.urlopen(url,timeout=2.5) as r:
            raw=r.read().decode('utf-8',errors='replace')
            try:data=json.loads(raw)
            except Exception:data=None
            return r.status, data if isinstance(data,dict) else None, None
    except urllib.error.HTTPError as e:
        raw=e.read().decode('utf-8',errors='replace')
        try:data=json.loads(raw)
        except Exception:data=None
        return e.code, data if isinstance(data,dict) else None, f'HTTPError:{e.code}'
    except Exception as e:
        return None,None,f'{type(e).__name__}:{e}'
def deep_get(d,*path):
    cur=d
    for key in path:
        if not isinstance(cur,dict): return None
        cur=cur.get(key)
    return cur
print('VERTEX_TEST_CARD_RETURNED_RERUN_READINESS_000122V5=BEGIN')
emit('MODE','READ_ONLY')
emit('TARGET_JOB_ID',JOB_ID)
emit('TARGET_ARTIFACT_ID',ARTIFACT_ID)
failures=[]
appdata=os.environ.get('APPDATA')
meta_hits=[]
if appdata:
    state_dir=Path(appdata)/'vertex-session-portal'/'vra-dispatch'
    emit('PORTAL_STATE_DIR',str(state_dir))
    if state_dir.exists():
        for p in state_dir.glob('*.meta.json'):
            obj=load_json(p)
            if obj and obj.get('job_id')==JOB_ID: meta_hits.append((p,obj))
else:
    emit('PORTAL_STATE_DIR','APPDATA_UNAVAILABLE')
emit('PORTAL_META_HIT_COUNT',len(meta_hits))
portal_meta=None
if len(meta_hits)==1:
    meta_path,portal_meta=meta_hits[0]
    emit('PORTAL_META_PATH',str(meta_path))
    core_keys=['contract_version','capture_id','job_id','correlation_id','origin_vera','origin_session','origin_window','artifact_id','card_kind','rerun_of_job_id','test_run_id','human_approval','dispatch_phase','status','workstation_registration','workstation_job_state','workstation_evidence_state','workstation_evidence_return_state','evidence_identity','evidence_cache_name','error','workstation_last_error']
    for k in core_keys: emit('PORTAL_'+k.upper(),portal_meta.get(k))
    extra={k:v for k,v in portal_meta.items() if any(t in k.lower() for t in ('delivery','ack','return')) and k not in core_keys}
    emit('PORTAL_DELIVERY_ACK_EXTRA',extra)
    if portal_meta.get('artifact_id')!=ARTIFACT_ID: failures.append('PORTAL_ARTIFACT_ID_MISMATCH')
    if portal_meta.get('card_kind')!='TEST': failures.append('PORTAL_CARD_KIND_NOT_TEST')
elif len(meta_hits)==0: failures.append('PORTAL_META_NOT_FOUND')
else: failures.append('PORTAL_META_DUPLICATE')
job_status,job_json,job_err=http_json(f'{WORKSTATION_BASE}/v1/jobs/{JOB_ID}')
ev_status,ev_json,ev_err=http_json(f'{WORKSTATION_BASE}/v1/jobs/{JOB_ID}/evidence')
emit('WORKSTATION_JOB_HTTP',job_status); emit('WORKSTATION_JOB_ERROR',job_err)
emit('WORKSTATION_EVIDENCE_HTTP',ev_status); emit('WORKSTATION_EVIDENCE_ERROR',ev_err)
ws_job_artifact=deep_get(job_json,'job','artifact_id') or deep_get(job_json,'artifact_id') or deep_get(job_json,'job','record','artifact_id')
ws_return_state=deep_get(ev_json,'evidence','evidence_return_state') or deep_get(ev_json,'evidence_return_state')
ws_returned_at=deep_get(ev_json,'evidence','evidence_returned_at') or deep_get(ev_json,'evidence_returned_at')
ws_evidence_state=deep_get(ev_json,'evidence','evidence_state') or deep_get(ev_json,'evidence_state')
ws_evidence_id=deep_get(ev_json,'evidence','envelope','evidence_id') or deep_get(ev_json,'envelope','evidence_id')
ws_origin_session=deep_get(ev_json,'evidence','envelope','origin','origin_session') or deep_get(ev_json,'envelope','origin','origin_session')
ws_required_auth=deep_get(ev_json,'evidence','envelope','required_reexecution_authority') or deep_get(ev_json,'envelope','required_reexecution_authority')
emit('WORKSTATION_JOB_ARTIFACT_ID',ws_job_artifact); emit('WORKSTATION_EVIDENCE_STATE',ws_evidence_state); emit('WORKSTATION_RETURN_STATE',ws_return_state); emit('WORKSTATION_RETURNED_AT',ws_returned_at); emit('WORKSTATION_EVIDENCE_ID',ws_evidence_id); emit('WORKSTATION_ORIGIN_SESSION',ws_origin_session); emit('WORKSTATION_REQUIRED_REEXECUTION_AUTHORITY',ws_required_auth)
if job_status==200 and ws_job_artifact not in (None,ARTIFACT_ID): failures.append('WORKSTATION_ARTIFACT_ID_MISMATCH')
if ev_status==200:
    if ws_origin_session!='vera-05': failures.append('WORKSTATION_ORIGIN_SESSION_MISMATCH')
    if ws_required_auth!='HUMAN_APPLY': failures.append('WORKSTATION_REEXECUTION_AUTHORITY_MISMATCH')
source_checks={
'src/main/vra/vra-dispatch-service.ts':['acknowledgeEvidenceDelivery','required_reexecution_authority','VRA_TEST_CARD_KIND','rerunOfJobId','testRunId'],
'src/main/ipc/register-vra-dispatch-ipc.ts':['workstation:vra-evidence-ack','acknowledgeEvidenceDelivery'],
'src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts':['cardKind','rerunOfJobId','testRunId']}
for rel,needles in source_checks.items():
    p=PORTAL_ROOT/rel; emit(f'SOURCE_EXISTS::{rel}',p.exists())
    if not p.exists(): failures.append(f'SOURCE_MISSING::{rel}'); continue
    text=p.read_text(encoding='utf-8',errors='replace')
    for needle in needles:
        ok=needle in text; emit(f'SOURCE_HAS::{rel}::{needle}',ok)
        if not ok: failures.append(f'SOURCE_ANCHOR_MISSING::{rel}::{needle}')
renderer=PORTAL_ROOT/'src/renderer/src/components/VraDispatchLane/VraDispatchLane.ts'
if renderer.exists():
    rt=renderer.read_text(encoding='utf-8',errors='replace'); lower=rt.lower()
    emit('RENDERER_HAS_TEST_LITERAL',("'TEST'" in rt or '"TEST"' in rt))
    emit('RENDERER_HAS_RERUN_VOCAB',('rerun' in lower or 're-run' in lower or 'redispatch' in lower or '再発注' in rt))
portal_return_state=portal_meta.get('workstation_evidence_return_state') if portal_meta else None
portal_evidence_state=portal_meta.get('workstation_evidence_state') if portal_meta else None
if ws_return_state=='RETURNED':
    classification='READY_FOR_TEST_RERUN_UI_CHECK' if portal_return_state=='RETURNED' else 'WORKSTATION_RETURNED_PORTAL_RECONCILIATION_PENDING'
elif ws_return_state=='RETURN_QUEUED': classification='PORTAL_ACK_STILL_REQUIRED'
elif ev_status is None: classification='WORKSTATION_OFFLINE_OR_UNREACHABLE'
else: classification=f'UNEXPECTED_RETURN_STATE::{ws_return_state}'
emit('PORTAL_OBSERVED_EVIDENCE_STATE',portal_evidence_state); emit('PORTAL_OBSERVED_RETURN_STATE',portal_return_state); emit('CLASSIFICATION',classification)
emit('PRODUCTION_MUTATION','ZERO'); emit('HTTP_MUTATING_REQUESTS','ZERO'); emit('ACK_POST_EXECUTED','NO'); emit('RERUN_EXECUTED','NO')
if failures:
    emit('STRUCTURAL_FAILURES',failures); print('VERTEX_TEST_CARD_RETURNED_RERUN_READINESS_000122V5=FAIL'); sys.exit(1)
print('STRUCTURAL_FAILURES=[]'); print('VERTEX_TEST_CARD_RETURNED_RERUN_READINESS_000122V5=PASS')
