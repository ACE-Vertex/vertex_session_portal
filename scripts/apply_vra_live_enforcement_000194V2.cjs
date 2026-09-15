
const fs=require('fs');
const path=require('path');

let parser;
try{parser=require('@babel/parser');}catch(e){process.exit(5201);}
if(!parser||typeof parser.parse!=='function') process.exit(5202);

const ROOT=process.cwd();
const SRC=path.join(ROOT,'src');
const POST_GATE=/READY_FOR_BAY|DISPATCHED|EVIDENCE_AVAILABLE|RETURN_QUEUED|RETURNED|publication|publish/i;

function walk(dir,out=[]){
  if(!fs.existsSync(dir)) return out;
  for(const ent of fs.readdirSync(dir,{withFileTypes:true})){
    const p=path.join(dir,ent.name);
    if(ent.isDirectory()) walk(p,out);
    else if(/\.(ts|tsx|mts|cts)$/.test(ent.name)) out.push(p);
  }
  return out;
}
function rel(p){return path.relative(ROOT,p).replace(/\\/g,'/');}
function parseFile(file,raw){
  const plugins=['typescript','decorators-legacy','classProperties','classPrivateProperties',
    'classPrivateMethods','topLevelAwait','importMeta'];
  if(file.endsWith('.tsx')) plugins.push('jsx');
  return parser.parse(raw,{sourceType:'unambiguous',errorRecovery:true,plugins});
}
function text(raw,node){
  return node&&Number.isInteger(node.start)&&Number.isInteger(node.end)?raw.slice(node.start,node.end):'';
}
function keyName(k){
  if(!k) return '';
  if(k.type==='Identifier') return k.name;
  if(k.type==='StringLiteral') return String(k.value);
  return '';
}
function isFn(n){
  return !!n&&['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression',
    'ObjectMethod','ClassMethod','ClassPrivateMethod'].includes(n.type);
}
function unwrap(n){
  let x=n,g=0;
  while(x&&g++<24&&[
    'TSAsExpression','TSTypeAssertion','TSNonNullExpression','TypeCastExpression',
    'ParenthesizedExpression','ChainExpression','AwaitExpression',
    'TSInstantiationExpression','TSConstAssertion','TSSatisfiesExpression'
  ].includes(x.type)) x=x.expression||x.argument;
  return x;
}
function memberChain(node){
  const n=unwrap(node);
  if(!n) return '';
  if(n.type==='Identifier') return n.name;
  if(n.type==='ThisExpression') return 'this';
  if(n.type==='MemberExpression'||n.type==='OptionalMemberExpression'){
    const l=memberChain(n.object);
    let r='';
    if(!n.computed&&n.property&&n.property.type==='Identifier') r=n.property.name;
    else if(n.computed&&n.property&&n.property.type==='StringLiteral') r=String(n.property.value);
    else return '';
    return l?l+'.'+r:r;
  }
  return '';
}
function terminalName(node){
  const n=unwrap(node);
  if(!n) return '';
  if(n.type==='Identifier') return n.name;
  if(n.type==='MemberExpression'||n.type==='OptionalMemberExpression'){
    if(!n.computed&&n.property&&n.property.type==='Identifier') return n.property.name;
    if(n.computed&&n.property&&n.property.type==='StringLiteral') return String(n.property.value);
  }
  return '';
}
function containsIdentifier(node,name){
  let found=false;
  function visit(n){
    if(!n||typeof n!=='object'||found) return;
    if(n.type==='Identifier'&&n.name===name){found=true;return;}
    if(n!==node&&isFn(n)) return;
    for(const [k,v] of Object.entries(n)){
      if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
      if(Array.isArray(v)){
        for(const c of v) if(c&&typeof c==='object'&&typeof c.type==='string') visit(c);
      }else if(v&&typeof v==='object'&&typeof v.type==='string') visit(v);
    }
  }
  visit(node); return found;
}
function pathParamNames(fn){
  const s=new Set();
  for(const p of fn.node.params||[]){
    let n='';
    if(p.type==='Identifier') n=p.name;
    else if(p.type==='AssignmentPattern'&&p.left&&p.left.type==='Identifier') n=p.left.name;
    if(/file|path|archive|bundle|vra|incoming|source|input/i.test(n)) s.add(n);
  }
  return s;
}
function callClass(call){
  const s=memberChain(call.callee).toLowerCase();
  if(/registry|register|lifecycle|ledger/.test(s)) return 1;
  if(/persist|store|save|insert|update|upsert|put|write|record|commit|append|add/.test(s)) return 2;
  if(/card|approv|human.?gate|\bgate\b/.test(s)) return 3;
  return 8;
}

const parsed=[];
for(const file of walk(SRC)){
  const r=rel(file);
  if(/vra-policy-validator\.ts$/i.test(r)) continue;
  if(/system-policy-registry\.ts$/i.test(r)) continue;
  if(/vertex-contract-catalog\.ts$/i.test(r)) continue;
  if(/\.test\.|\.spec\./i.test(r)) continue;
  let raw;try{raw=fs.readFileSync(file,'utf8')}catch{continue}
  let ast;try{ast=parseFile(file,raw)}catch{continue}
  parsed.push({file,raw,ast,r});
}
if(!parsed.length) process.exit(5203);

const funcs=[];
const defsByName=new Map();

function addFn(name,F,node,ownerClass=''){
  const fn={name:name||'<anonymous>',file:F.r,node,body:text(F.raw,node),F,ownerClass};
  funcs.push(fn);
  if(name){
    if(!defsByName.has(name)) defsByName.set(name,[]);
    defsByName.get(name).push(fn);
  }
}
for(const F of parsed.filter(F=>!/\/renderer\//.test(F.r))){
  function visit(node,ownerClass=''){
    if(!node||typeof node!=='object') return;

    let cls=ownerClass;
    if(node.type==='ClassDeclaration'&&node.id&&node.id.type==='Identifier') cls=node.id.name;
    if(node.type==='ClassExpression'&&node.id&&node.id.type==='Identifier') cls=node.id.name;

    if(node.type==='FunctionDeclaration') addFn(node.id&&node.id.name,F,node,ownerClass);
    else if(['ObjectMethod','ClassMethod','ClassPrivateMethod'].includes(node.type)) addFn(keyName(node.key),F,node,ownerClass);
    else if(node.type==='VariableDeclarator'&&node.id&&node.id.type==='Identifier'&&node.init&&
      ['ArrowFunctionExpression','FunctionExpression'].includes(node.init.type)) addFn(node.id.name,F,node.init,ownerClass);
    else if(node.type==='ObjectProperty'&&node.value&&
      ['ArrowFunctionExpression','FunctionExpression'].includes(node.value.type)) addFn(keyName(node.key),F,node.value,ownerClass);

    for(const [k,v] of Object.entries(node)){
      if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
      if(Array.isArray(v)){
        for(const c of v) if(c&&typeof c==='object'&&typeof c.type==='string') visit(c,cls);
      }else if(v&&typeof v==='object'&&typeof v.type==='string') visit(v,cls);
    }
  }
  visit(F.ast,'');
}

function sig(fn){
  const s=fn.file+'\n'+fn.name+'\n'+fn.body;
  const low=s.toLowerCase();
  return {
    vra:
      /\.vra\b/i.test(s) ||
      /\bvra\b/i.test(fn.name) ||
      /vra[-_]/i.test(fn.file) ||
      /artifact_?id|origin_vera|return_channel|schema_version/i.test(s),
    intake:/intake|ingest|incoming|receive|accept|import|drop|watch|scan|pickup|discover/i.test(low),
    startup:/startup|initialize|initialise|\binit\b|bootstrap|restore|recover|reload|snapshot/i.test(low),
    card:/card|approv|human.?gate|\bgate\b/i.test(low)
  };
}

const anchors=[];
for(const fn of funcs){
  if(POST_GATE.test(fn.body||'')) continue;
  const s=sig(fn);
  if(!s.vra||!s.intake||s.startup||s.card) continue;
  anchors.push(fn);
}
if(!anchors.length) process.exit(5204);

const chains=[];

for(const fn of anchors){
  const pathNames=pathParamNames(fn);

  const locals=new Map();
  const params=new Set();
  const imports=new Map();

  for(const p of fn.node.params||[]){
    if(p.type==='Identifier') params.add(p.name);
    else if(p.type==='AssignmentPattern'&&p.left&&p.left.type==='Identifier') params.add(p.left.name);
  }

  for(const stmt of fn.F.ast.program.body||[]){
    if(stmt.type==='ImportDeclaration'){
      const src=stmt.source&&stmt.source.value?String(stmt.source.value):'';
      for(const sp of stmt.specifiers||[]){
        if(sp.local&&sp.local.type==='Identifier') imports.set(sp.local.name,src);
      }
    }
  }

  function collectLocals(n){
    if(!n||typeof n!=='object') return;
    if(n!==fn.node&&isFn(n)) return;
    if(n.type==='VariableDeclarator'&&n.id&&n.id.type==='Identifier'){
      locals.set(n.id.name,unwrap(n.init));
    }
    for(const [k,v] of Object.entries(n)){
      if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
      if(Array.isArray(v)){
        for(const c of v) if(c&&typeof c==='object'&&typeof c.type==='string') collectLocals(c);
      }else if(v&&typeof v==='object'&&typeof v.type==='string') collectLocals(v);
    }
  }
  collectLocals(fn.node);

  const calls=[];
  function collectCalls(n){
    if(!n||typeof n!=='object') return;
    if(n!==fn.node&&isFn(n)) return;
    if(n.type==='CallExpression'||n.type==='OptionalCallExpression') calls.push(n);
    for(const [k,v] of Object.entries(n)){
      if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
      if(Array.isArray(v)){
        for(const c of v) if(c&&typeof c==='object'&&typeof c.type==='string') collectCalls(c);
      }else if(v&&typeof v==='object'&&typeof v.type==='string') collectCalls(v);
    }
  }
  collectCalls(fn.node);

  function receivesPath(call){
    for(const a of call.arguments||[]){
      for(const pn of pathNames){
        if(containsIdentifier(a,pn)) return true;
      }
    }
    return false;
  }

  function bindingOf(call){
    let result=null;
    function visit(n){
      if(!n||typeof n!=='object'||result) return;
      if(n!==fn.node&&isFn(n)) return;
      if(n.type==='VariableDeclarator'&&unwrap(n.init)===call&&n.id&&n.id.type==='Identifier'){
        result={name:n.id.name,start:n.start};
        return;
      }
      if(n.type==='AssignmentExpression'&&unwrap(n.right)===call&&n.left&&n.left.type==='Identifier'){
        result={name:n.left.name,start:n.start};
        return;
      }
      for(const [k,v] of Object.entries(n)){
        if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
        if(Array.isArray(v)){
          for(const c of v) if(c&&typeof c==='object'&&typeof c.type==='string') visit(c);
        }else if(v&&typeof v==='object'&&typeof v.type==='string') visit(v);
      }
    }
    visit(fn.node); return result;
  }

  function downstream(binding){
    let registry=false,persist=false,card=false;
    function visit(n){
      if(!n||typeof n!=='object') return;
      if(n!==fn.node&&isFn(n)) return;
      if(
        (n.type==='CallExpression'||n.type==='OptionalCallExpression') &&
        Number.isInteger(n.start) &&
        n.start>binding.start &&
        containsIdentifier(n,binding.name)
      ){
        const cls=callClass(n);
        if(cls===1) registry=true;
        else if(cls===2) persist=true;
        else if(cls===3) card=true;
      }
      for(const [k,v] of Object.entries(n)){
        if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
        if(Array.isArray(v)){
          for(const c of v) if(c&&typeof c==='object'&&typeof c.type==='string') visit(c);
        }else if(v&&typeof v==='object'&&typeof v.type==='string') visit(v);
      }
    }
    visit(fn.node); return {registry,persist,card};
  }

  for(const call of calls){
    if(!receivesPath(call)) continue;
    const binding=bindingOf(call);
    if(!binding) continue;
    const d=downstream(binding);
    if(!(d.registry||d.persist)||d.card) continue;

    chains.push({anchor:fn,call,binding,down:d,locals,params,imports});
  }
}

if(chains.length!==1) process.exit(5205);
const c=chains[0];


const childProcess=require('child_process');

const VALIDATOR_PATH=path.join(ROOT,'src','shared','vra-policy-validator.ts');
if(!fs.existsSync(VALIDATOR_PATH)) process.exit(5401);

const validatorRaw=fs.readFileSync(VALIDATOR_PATH,'utf8');
if(!(
  /export\s+(?:function|const)\s+validateVraAgainstActivePolicy\b/.test(validatorRaw) ||
  /export\s*\{[^}]*validateVraAgainstActivePolicy[^}]*\}/s.test(validatorRaw)
)) process.exit(5402);

if(!(
  /\bvalid\s*:\s*boolean\b/.test(validatorRaw) ||
  /\bvalid\s*:\s*(?:true|false)\b/.test(validatorRaw) ||
  /return\s*\{[\s\S]{0,500}\bvalid\s*:/m.test(validatorRaw)
)) process.exit(5403);

const anchor=c.anchor;
const anchorPath=anchor.F.file;
const anchorRaw=anchor.F.raw;

function buildParentMap(root){
  const p=new WeakMap();
  function visit(n,parent=null){
    if(!n||typeof n!=='object') return;
    if(parent) p.set(n,parent);
    for(const [k,v] of Object.entries(n)){
      if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
      if(Array.isArray(v)){
        for(const x of v) if(x&&typeof x==='object'&&typeof x.type==='string') visit(x,n);
      }else if(v&&typeof v==='object'&&typeof v.type==='string') visit(v,n);
    }
  }
  visit(root,null);
  return p;
}
const parents=buildParentMap(anchor.node);

let bindingDecl=null;
function findBinding(n){
  if(!n||typeof n!=='object'||bindingDecl) return;
  if(n!==anchor.node&&isFn(n)) return;
  if(
    n.type==='VariableDeclarator' &&
    n.id && n.id.type==='Identifier' &&
    n.id.name===c.binding.name &&
    unwrap(n.init)===c.call
  ){
    bindingDecl=n;
    return;
  }
  for(const [k,v] of Object.entries(n)){
    if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
    if(Array.isArray(v)){
      for(const x of v) if(x&&typeof x==='object'&&typeof x.type==='string') findBinding(x);
    }else if(v&&typeof v==='object'&&typeof v.type==='string') findBinding(v);
  }
}
findBinding(anchor.node);
if(!bindingDecl) process.exit(5404);

let bindingStmt=null;
{
  let p=parents.get(bindingDecl);
  while(p && p!==anchor.node){
    if(p.type==='VariableDeclaration'){bindingStmt=p;break;}
    p=parents.get(p);
  }
}
if(!bindingStmt) process.exit(5405);

let firstConsumer=null;
function findConsumer(n){
  if(!n||typeof n!=='object') return;
  if(n!==anchor.node&&isFn(n)) return;
  if(
    (n.type==='CallExpression'||n.type==='OptionalCallExpression') &&
    Number.isInteger(n.start) &&
    n.start>c.binding.start &&
    containsIdentifier(n,c.binding.name)
  ){
    const cls=callClass(n);
    if(cls===1||cls===2){
      if(!firstConsumer || n.start<firstConsumer.start) firstConsumer=n;
    }
  }
  for(const [k,v] of Object.entries(n)){
    if(['loc','start','end','extra','errors','comments','tokens'].includes(k)) continue;
    if(Array.isArray(v)){
      for(const x of v) if(x&&typeof x==='object'&&typeof x.type==='string') findConsumer(x);
    }else if(v&&typeof v==='object'&&typeof v.type==='string') findConsumer(v);
  }
}
findConsumer(anchor.node);
if(!firstConsumer || !(bindingStmt.end<firstConsumer.start)) process.exit(5406);

const cal=unwrap(c.call.callee);
const term=terminalName(cal);
const defs=(defsByName.get(term)||[]).filter(d=>!POST_GATE.test(d.body||''));
if(defs.length!==1) process.exit(5407);

const producer=defs[0];
const producerText=(producer.file+'\n'+producer.ownerClass+'\n'+producer.name+'\n'+producer.body);
const producerLow=producerText.toLowerCase();

if(!/schema_version|artifact_id|authority|routing|operations|verification|return_channel|origin_vera/.test(producerLow)){
  process.exit(5408);
}
if(!/vra|manifest|artifact/.test((producer.file+'\n'+producer.ownerClass+'\n'+producer.name).toLowerCase())){
  process.exit(5409);
}
if(/startup|initialize|initialise|\binit\b|bootstrap|restore|recover|reload|snapshot/.test(producerLow)){
  process.exit(5410);
}
if(sig(anchor).startup || sig(anchor).card || /\/renderer\//i.test(anchor.file)){
  process.exit(5411);
}

const validatorRelNoExt=path.relative(path.dirname(anchorPath),VALIDATOR_PATH)
  .replace(/\\/g,'/')
  .replace(/\.(ts|tsx|mts|cts)$/i,'');
const importSpec=validatorRelNoExt.startsWith('.')?validatorRelNoExt:'./'+validatorRelNoExt;

const resolved=path.resolve(path.dirname(anchorPath),importSpec+'.ts');
if(path.normalize(resolved)!==path.normalize(VALIDATOR_PATH)) process.exit(5412);

const tempName='vraPolicyValidation';
const importMarker='validateVraAgainstActivePolicy';
const callMarker='validateVraAgainstActivePolicy('+c.binding.name+')';

if(anchorRaw.includes(importMarker) && anchorRaw.includes(callMarker)){
  const valIdx=anchorRaw.indexOf(callMarker);
  const consumerSnippet=text(anchorRaw,firstConsumer);
  const consumerIdx=consumerSnippet?anchorRaw.indexOf(consumerSnippet,valIdx+1):-1;

  if(
    valIdx>=0 &&
    consumerIdx>valIdx &&
    new RegExp('if\\s*\\(\\s*!\\s*'+tempName.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\.valid\\s*\\)').test(anchorRaw) &&
    /throw\s+new\s+Error\s*\(/.test(anchorRaw.slice(valIdx,consumerIdx))
  ){
    process.exit(0);
  }
  process.exit(5413);
}

if(anchorRaw.includes(importMarker) || new RegExp('\\b'+tempName+'\\b').test(anchorRaw)){
  process.exit(5414);
}

const lineStart=anchorRaw.lastIndexOf('\n',Math.max(0,bindingStmt.start-1))+1;
const prefixText=anchorRaw.slice(lineStart,bindingStmt.start);
const indent=(prefixText.match(/^\s*/)||[''])[0];

const injection=
  '\n'+indent+'const '+tempName+' = validateVraAgainstActivePolicy('+c.binding.name+');'+
  '\n'+indent+'if (!'+tempName+'.valid) {'+
  '\n'+indent+'  throw new Error("VRA rejected by active System Policy");'+
  '\n'+indent+'}\n';

const importLine="import { validateVraAgainstActivePolicy } from '"+importSpec+"';\n";

let importPos=0;
for(const stmt of anchor.F.ast.program.body||[]){
  if(stmt.type==='ImportDeclaration') importPos=stmt.end;
}
if(importPos>0){
  const nl=anchorRaw.indexOf('\n',importPos);
  importPos=nl<0?anchorRaw.length:nl+1;
}

const edits=[
  {pos:bindingStmt.end,text:injection},
  {pos:importPos,text:importLine}
].sort((a,b)=>b.pos-a.pos);

let patched=anchorRaw;
for(const e of edits){
  patched=patched.slice(0,e.pos)+e.text+patched.slice(e.pos);
}

try{
  parseFile(anchorPath,patched);
}catch(e){
  process.exit(5415);
}

const valIdx=patched.indexOf(callMarker);
const consumerSnippet=text(anchorRaw,firstConsumer);
const consumerIdx=consumerSnippet?patched.indexOf(consumerSnippet,valIdx+1):-1;

if(valIdx<0 || consumerIdx<=valIdx) process.exit(5416);
if(!new RegExp('if\\s*\\(\\s*!\\s*'+tempName.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\.valid\\s*\\)').test(patched)){
  process.exit(5417);
}
if(!/throw\s+new\s+Error\s*\("VRA rejected by active System Policy"\)/.test(patched.slice(valIdx,consumerIdx))){
  process.exit(5418);
}

const tmpPath=anchorPath+'.vertex-live-enforcement-000194.tmp';
try{
  fs.writeFileSync(tmpPath,patched,'utf8');
  fs.renameSync(tmpPath,anchorPath);

  const written=fs.readFileSync(anchorPath,'utf8');
  parseFile(anchorPath,written);

  const writtenValIdx=written.indexOf(callMarker);
  const writtenConsumerIdx=consumerSnippet?written.indexOf(consumerSnippet,writtenValIdx+1):-1;

  if(writtenValIdx<0 || writtenConsumerIdx<=writtenValIdx){
    throw new Error('validator ordering verification failed');
  }
  if(!written.includes(importLine.trim())){
    throw new Error('validator import verification failed');
  }
  if(!new RegExp('if\\s*\\(\\s*!\\s*'+tempName.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'\\.valid\\s*\\)').test(written)){
    throw new Error('fail-closed guard verification failed');
  }

  const pkgPath=path.join(ROOT,'package.json');
  if(fs.existsSync(pkgPath)){
    let pkg=null;
    try{pkg=JSON.parse(fs.readFileSync(pkgPath,'utf8'));}catch{}
    if(pkg&&pkg.scripts&&typeof pkg.scripts.typecheck==='string'){
      let cmd='npm';
      if(fs.existsSync(path.join(ROOT,'pnpm-lock.yaml'))) cmd='pnpm';
      else if(fs.existsSync(path.join(ROOT,'yarn.lock'))) cmd='yarn';

      const r=childProcess.spawnSync(
        cmd,
        ['run','typecheck'],
        {cwd:ROOT,encoding:'utf8',shell:true,timeout:120000}
      );
      if(r.error || r.status!==0){
        throw new Error('project typecheck failed');
      }
    }
  }

  process.exit(0);
}catch(e){
  try{ if(fs.existsSync(tmpPath)) fs.unlinkSync(tmpPath); }catch{}
  try{ fs.writeFileSync(anchorPath,anchorRaw,'utf8'); }catch{}
  process.exit(5419);
}
