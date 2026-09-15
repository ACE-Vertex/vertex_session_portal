
const fs=require('fs'), path=require('path'), cp=require('child_process');
let parser;
try{parser=require('@babel/parser')}catch{process.exit(6101)}
if(!parser||typeof parser.parse!=='function') process.exit(6102);

const ROOT=process.cwd();
const SHARED=path.join(ROOT,'src','shared');
const CAT=path.join(SHARED,'vertex-contract-catalog.ts');
const POL=path.join(SHARED,'system-policy-registry.ts');
const VAL=path.join(SHARED,'vra-policy-validator.ts');
const TARGET=path.join(SHARED,'vra-builder.ts');

function read(p){try{return fs.readFileSync(p,'utf8')}catch{return ''}}
const cat=read(CAT), pol=read(POL), val=read(VAL);
if(!cat||!pol||!val) process.exit(6103);

function parseTs(raw,file='x.ts'){
  return parser.parse(raw,{
    sourceType:'unambiguous',
    errorRecovery:false,
    plugins:['typescript','decorators-legacy','classProperties','classPrivateProperties',
      'classPrivateMethods','topLevelAwait','importMeta']
  });
}
const ast=parseTs(cat,CAT);

function keyName(k){
  if(!k)return '';
  if(k.type==='Identifier')return k.name;
  if(k.type==='StringLiteral')return String(k.value);
  return '';
}
function lit(n){
  if(!n)return undefined;
  if(n.type==='StringLiteral')return n.value;
  if(n.type==='TemplateLiteral'&&n.expressions.length===0)
    return n.quasis.map(q=>q.value.cooked||q.value.raw).join('');
  return undefined;
}
function containsIssue(n){
  let yes=false;
  function w(x){
    if(!x||typeof x!=='object'||yes)return;
    const v=lit(x);
    if(typeof v==='string'&&v.includes('vertex.vra.issue/1')){yes=true;return}
    for(const [k,z] of Object.entries(x)){
      if(['loc','start','end','extra','comments','tokens','errors'].includes(k))continue;
      if(Array.isArray(z)){for(const c of z) if(c&&typeof c==='object')w(c)}
      else if(z&&typeof z==='object')w(z);
    }
  }
  w(n);return yes;
}

// Locate canonical issuance entry.
let issueEntry=null;
function findIssue(n){
  if(!n||typeof n!=='object'||issueEntry)return;
  if(n.type==='ObjectExpression'&&containsIssue(n)){issueEntry=n;return}
  for(const [k,z] of Object.entries(n)){
    if(['loc','start','end','extra','comments','tokens','errors'].includes(k))continue;
    if(Array.isArray(z)){for(const c of z) if(c&&typeof c==='object')findIssue(c)}
    else if(z&&typeof z==='object')findIssue(z);
  }
}
findIssue(ast);
if(!issueEntry) process.exit(6104);

// Locate exactly one exported Catalog getter/resolver.
const getters=[];
for(const stmt of ast.program.body||[]){
  if(stmt.type!=='ExportNamedDeclaration'||!stmt.declaration)continue;
  const d=stmt.declaration;
  if(d.type==='FunctionDeclaration'&&d.id){
    const n=d.id.name;
    if(/resolve|get|find|lookup/i.test(n)&&/contract|catalog|entry|record/i.test(n))
      getters.push({name:n,params:d.params||[]});
  }else if(d.type==='VariableDeclaration'){
    for(const dec of d.declarations||[]){
      if(dec.id&&dec.id.type==='Identifier'&&dec.init&&
         ['ArrowFunctionExpression','FunctionExpression'].includes(dec.init.type)){
        const n=dec.id.name;
        if(/resolve|get|find|lookup/i.test(n)&&/contract|catalog|entry|record/i.test(n))
          getters.push({name:n,params:dec.init.params||[]});
      }
    }
  }
}
const uniq=[...new Map(getters.map(g=>[g.name,g])).values()];
if(uniq.length!==1) process.exit(6105);
const getter=uniq[0];

// Resolve active-policy contract reference field.
const refMatch=pol.match(/([A-Za-z_$][\w$]*)\s*:\s*['"](vertex\.vra\.issue\/1(?:@[\w.-]+)?)['"]/);
if(!refMatch) process.exit(6106);
const contractField=refMatch[1];

const verMatch=pol.match(/([A-Za-z_$][\w$]*(?:version|Version)[\w$]*)\s*:\s*['"]([0-9]+\.[0-9]+\.[0-9]+)['"]/)
  || pol.match(/\b(version)\s*:\s*['"]([0-9]+\.[0-9]+\.[0-9]+)['"]/);
const versionField=verMatch?verMatch[1]:'version';

// Find smallest complete machine-readable canonical profile.
const profiles=[];
function classifyProfile(n){
  if(!n||n.type!=='ObjectExpression')return null;
  let schema=false,authority=false,routing=false,ret=false,lane=false,copy=false,payload=false,sha=false;

  function walk(x){
    if(!x||typeof x!=='object')return;
    if(x.type==='ObjectProperty'){
      const k=keyName(x.key), v=lit(x.value);
      const r=cat.slice(x.start||0,x.end||0);
      if(k==='schema_version'&&v==='vra/1')schema=true;
      if(k==='authority'&&v==='HUMAN_APPLY')authority=true;
      if(k==='contract_version'&&v==='vra-routing/1')routing=true;
      if(k==='return_channel'&&v==='vertex-session-portal:return-queue')ret=true;
      if(/lane[_-]?policy|allowed|values|enum/i.test(k+' '+r)&&/\bANY\b/.test(r)&&/\bPREFER\b/.test(r))lane=true;
      if(/operation|operations|\bop\b/i.test(k+' '+r)&&/\bcopy\b/.test(r))copy=true;
      if(/payload|source_prefix|prefix/i.test(k+' '+r)&&/payload\//.test(r))payload=true;
      if(/sha256|hash|digest/i.test(k+' '+r)&&/64|hex|lowercase|sha256/i.test(r))sha=true;
    }
    for(const [k,z] of Object.entries(x)){
      if(['loc','start','end','extra','comments','tokens','errors'].includes(k))continue;
      if(Array.isArray(z)){for(const c of z)if(c&&typeof c==='object')walk(c)}
      else if(z&&typeof z==='object')walk(z);
    }
  }
  walk(n);
  return {schema,authority,routing,ret,lane,copy,payload,sha,
    full:schema&&authority&&routing&&ret&&lane&&copy&&payload&&sha};
}
function scanObjects(n){
  if(!n||typeof n!=='object')return;
  if(n.type==='ObjectExpression'){
    const c=classifyProfile(n);
    if(c&&c.full)profiles.push({node:n,c});
  }
  for(const [k,z] of Object.entries(n)){
    if(['loc','start','end','extra','comments','tokens','errors'].includes(k))continue;
    if(Array.isArray(z)){for(const c of z)if(c&&typeof c==='object')scanObjects(c)}
    else if(z&&typeof z==='object')scanObjects(z);
  }
}
scanObjects(issueEntry);
if(!profiles.length) process.exit(6107);
profiles.sort((a,b)=>(a.node.end-a.node.start)-(b.node.end-b.node.start));
const profile=profiles[0].node;

// Derive static property path from issue entry to canonical profile.
let foundPath=null;
function findPath(cur,target,segments){
  if(foundPath)return;
  if(cur===target){foundPath=segments.slice();return}
  if(!cur||typeof cur!=='object')return;
  if(cur.type==='ObjectExpression'){
    for(const p of cur.properties||[]){
      if(p.type!=='ObjectProperty')continue;
      const k=keyName(p.key);
      if(!k)continue;
      const v=p.value;
      if(v===target){foundPath=[...segments,k];return}
      if(v&&v.type==='ObjectExpression')findPath(v,target,[...segments,k]);
    }
  }
}
if(issueEntry===profile)foundPath=[];
else findPath(issueEntry,profile,[]);
if(foundPath===null) process.exit(6108);

// The preflight proved a one-argument getter, but keep generation safe if source evolves.
const getterCall=getter.params.length>=2
  ? `(getContract as unknown as (id: string, version: string) => unknown)(contractRef, policyVersion)`
  : `(getContract as unknown as (id: string) => unknown)(contractRef)`;

const pathLiteral=JSON.stringify(foundPath);

const source=`import { resolveActiveSystemPolicy } from './system-policy-registry'
import { ${getter.name} as getContract } from './vertex-contract-catalog'
import { validateVraAgainstActivePolicy, type VraValidationResult } from './vra-policy-validator'

export interface VraBuilderInput {
  readonly artifact_id: string
  readonly title: string
  readonly source: Readonly<{ actor: string; model: string }>
  readonly target: Readonly<{ project_root: string }>
  readonly routing: Readonly<{
    job_id: string
    origin_vera: string
    origin_session: string
    origin_window: string
    project_id: string
    project_name: string
    correlation_id: string
    lane_policy: 'ANY' | 'PREFER'
  }>
  readonly operations: readonly unknown[]
  readonly verification: readonly unknown[]
  readonly card_kind?: 'TEST'
}

export interface VraBuilderResult {
  readonly manifest: unknown
  readonly validation: VraValidationResult
}

function asRecord(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(label)
  }
  return value as Record<string, unknown>
}

function readStaticPath(root: unknown, segments: readonly string[]): Record<string, unknown> {
  let current: unknown = root
  for (const segment of segments) {
    const record = asRecord(current, 'VRA_CONTRACT_PROFILE_INVALID')
    current = record[segment]
  }
  return asRecord(current, 'VRA_CONTRACT_PROFILE_INVALID')
}

function requireString(record: Record<string, unknown>, key: string): string {
  const value = record[key]
  if (typeof value !== 'string' || value.length === 0) {
    throw new Error('VRA_CONTRACT_PROFILE_MISSING_' + key)
  }
  return value
}

/**
 * Build a VRA manifest from the currently active System Policy and the
 * machine-readable canonical profile in the Contract Catalog.
 *
 * The LLM/issuer supplies variable work data. Fixed issuance semantics are
 * resolved from policy/catalog and the completed manifest is validated
 * deterministically before it can leave this boundary.
 */
export function buildVraFromActivePolicy(input: VraBuilderInput): VraBuilderResult {
  const policy = resolveActiveSystemPolicy('vertex.vra.issue')
  if (!policy) throw new Error('ACTIVE_VRA_ISSUANCE_POLICY_NOT_FOUND')

  const policyView = policy as unknown as Record<string, unknown>
  const contractRef = policyView['${contractField}']
  const versionValue = policyView['${versionField}']

  if (typeof contractRef !== 'string' || contractRef.length === 0) {
    throw new Error('ACTIVE_VRA_ISSUANCE_CONTRACT_REF_MISSING')
  }
  const policyVersion = typeof versionValue === 'string' ? versionValue : ''

  const contract = ${getterCall}
  if (!contract) throw new Error('ACTIVE_VRA_ISSUANCE_CONTRACT_NOT_FOUND')

  const profile = readStaticPath(contract, ${pathLiteral})
  const schemaVersion = requireString(profile, 'schema_version')
  const authority = requireString(profile, 'authority')

  const routingProfile =
    profile['routing'] && typeof profile['routing'] === 'object'
      ? asRecord(profile['routing'], 'VRA_ROUTING_PROFILE_INVALID')
      : profile

  const contractVersion = requireString(routingProfile, 'contract_version')
  const returnChannel = requireString(routingProfile, 'return_channel')

  const manifest: unknown = {
    schema_version: schemaVersion,
    artifact_id: input.artifact_id,
    title: input.title,
    source: input.source,
    target: input.target,
    authority,
    routing: {
      contract_version: contractVersion,
      job_id: input.routing.job_id,
      origin_vera: input.routing.origin_vera,
      origin_session: input.routing.origin_session,
      origin_window: input.routing.origin_window,
      return_channel: returnChannel,
      project_id: input.routing.project_id,
      project_name: input.routing.project_name,
      correlation_id: input.routing.correlation_id,
      lane_policy: input.routing.lane_policy
    },
    operations: input.operations,
    verification: input.verification,
    ...(input.card_kind ? { card_kind: input.card_kind } : {})
  }

  const validation = validateVraAgainstActivePolicy(manifest)
  if (!validation.valid) {
    throw new Error('VRA_BUILDER_POLICY_VALIDATION_FAILED')
  }

  return { manifest, validation }
}
`;

// Parse and structural verification before any production write.
try{parseTs(source,TARGET)}catch{process.exit(6109)}

const resolverIdx=source.indexOf("resolveActiveSystemPolicy(");
const catalogIdx=source.indexOf("const contract =");
const profileIdx=source.indexOf("readStaticPath(contract");
const validatorIdx=source.indexOf("validateVraAgainstActivePolicy(manifest)");
if(!(resolverIdx>=0&&catalogIdx>resolverIdx&&profileIdx>catalogIdx&&validatorIdx>profileIdx)) process.exit(6110);
if(!source.includes("throw new Error('VRA_BUILDER_POLICY_VALIDATION_FAILED')")) process.exit(6111);

// Idempotent success only if an already-present Builder is byte-identical.
if(fs.existsSync(TARGET)){
  const existing=fs.readFileSync(TARGET,'utf8');
  if(existing!==source) process.exit(6112);
}else{
  const tmp=TARGET+'.vertex-000201.tmp';
  try{
    fs.writeFileSync(tmp,source,'utf8');
    fs.renameSync(tmp,TARGET);
  }catch{
    try{if(fs.existsSync(tmp))fs.unlinkSync(tmp)}catch{}
    process.exit(6113);
  }
}

function runScript(name, timeout){
  const pkgPath=path.join(ROOT,'package.json');
  if(!fs.existsSync(pkgPath)) return true;
  let pkg=null;
  try{pkg=JSON.parse(fs.readFileSync(pkgPath,'utf8'))}catch{return false}
  if(!pkg||!pkg.scripts||typeof pkg.scripts[name]!=='string') return true;

  let cmd='npm';
  if(fs.existsSync(path.join(ROOT,'pnpm-lock.yaml')))cmd='pnpm';
  else if(fs.existsSync(path.join(ROOT,'yarn.lock')))cmd='yarn';

  const r=cp.spawnSync(cmd,['run',name],{cwd:ROOT,encoding:'utf8',shell:true,timeout});
  return !r.error&&r.status===0;
}

let ok=false;
try{
  const written=fs.readFileSync(TARGET,'utf8');
  parseTs(written,TARGET);

  if(!written.includes("buildVraFromActivePolicy")) throw new Error('missing builder export');
  if(!written.includes("resolveActiveSystemPolicy('vertex.vra.issue')")) throw new Error('missing policy resolver');
  if(!written.includes("readStaticPath(contract")) throw new Error('missing catalog profile read');
  if(!written.includes("validateVraAgainstActivePolicy(manifest)")) throw new Error('missing validator');
  if(!written.includes("VRA_BUILDER_POLICY_VALIDATION_FAILED")) throw new Error('missing fail closed');

  if(!runScript('typecheck',120000)) throw new Error('typecheck failed');
  if(!runScript('build',180000)) throw new Error('build failed');

  ok=true;
}catch{}

// Self-restore: this milestone creates a new file, so delete it on failure.
// Workstation recovery remains the outer safety boundary.
if(!ok){
  try{
    if(fs.existsSync(TARGET) && fs.readFileSync(TARGET,'utf8')===source) fs.unlinkSync(TARGET);
  }catch{}
  process.exit(6114);
}

process.exit(0);
