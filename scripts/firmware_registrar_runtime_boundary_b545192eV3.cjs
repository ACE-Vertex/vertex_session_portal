const fs = require('node:fs')
const path = require('node:path')
const { app } = require('electron')
const ts = require('typescript')

const ROOT = process.cwd()
const sourcePath = path.join(ROOT, 'src/main/firmware/FirmwareRegistrar.ts')
const tempRoot = path.join(ROOT, 'scripts', `.firmware-registrar-runtime-boundary-${process.pid}`)
const compiledPath = path.join(tempRoot, 'FirmwareRegistrar.cjs')

function emit(v) {
  console.log(String(v).replace(/[^\x20-\x7E]/g, ch => `\\u${ch.codePointAt(0).toString(16).padStart(4, '0')}`))
}

function die(code, label, detail = '') {
  emit(`RUNTIME_BOUNDARY=${label}`)
  if (detail) emit(`DETAIL=${detail}`)
  process.exitCode = code
  return false
}

function readJsonLines(filePath) {
  if (!fs.existsSync(filePath)) return []
  return fs.readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map(line => JSON.parse(line))
}

async function main() {
  fs.rmSync(tempRoot, { recursive: true, force: true })
  fs.mkdirSync(tempRoot, { recursive: true })
  app.setPath('userData', tempRoot)

  const source = fs.readFileSync(sourcePath, 'utf8')
  const transpiled = ts.transpileModule(source, {
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.CommonJS,
      esModuleInterop: true,
      moduleResolution: ts.ModuleResolutionKind.Node10,
    },
    fileName: sourcePath,
    reportDiagnostics: true,
  })

  const hard = (transpiled.diagnostics || []).filter(d => d.category === ts.DiagnosticCategory.Error)
  if (hard.length) {
    die(31, 'TRANSPILE_FAIL', hard.map(d => ts.flattenDiagnosticMessageText(d.messageText, ' ')).join(' | '))
    return
  }

  fs.writeFileSync(compiledPath, transpiled.outputText, 'utf8')
  const { FirmwareRegistrar } = require(compiledPath)
  const registrar = new FirmwareRegistrar()

  const now = new Date().toISOString()
  const green = {
    requestId: 'boundary-green-1',
    decision: 'APPROVE',
    decisionId: 'boundary-decision-green-1',
    decidedAt: now,
    target: 'test.firmware.runtime.boundary',
    proposedVersion: '1.0.0-test',
    risk: 'GREEN',
    validation: [{ label: 'runtime-validator', status: 'PASS', detail: 'boundary test' }],
    redConfirmed: false,
    source: { actor: 'VERA03', session: 'vera-03', reason: 'runtime boundary' },
  }

  let first
  try {
    first = registrar.register(green)
  } catch (e) {
    die(32, 'GREEN_REGISTER_THROW', String(e))
    return
  }
  if (!(first.accepted && first.committed && !first.idempotent && first.registryState === 'APPROVED')) {
    die(33, 'GREEN_RESULT_INVALID', JSON.stringify(first))
    return
  }
  emit('GREEN=PASS')

  let repeat
  try {
    repeat = registrar.register(green)
  } catch (e) {
    die(34, 'IDEMPOTENT_REPLAY_THROW', String(e))
    return
  }
  if (!(repeat.accepted && repeat.idempotent)) {
    die(35, 'IDEMPOTENT_RESULT_INVALID', JSON.stringify(repeat))
    return
  }
  emit('IDEMPOTENT=PASS')

  let validatorDenied = false
  try {
    registrar.register({
      ...green,
      requestId: 'boundary-validator-deny',
      decisionId: 'boundary-decision-validator-deny',
      proposedVersion: '1.0.1-test',
      validation: [{ label: 'runtime-validator', status: 'WARN' }],
    })
  } catch (e) {
    validatorDenied = String(e).includes('validator evidence is not all PASS')
  }
  if (!validatorDenied) {
    die(36, 'VALIDATOR_FAIL_CLOSED_BROKEN')
    return
  }
  emit('VALIDATOR_FAIL_CLOSED=PASS')

  let redDenied = false
  try {
    registrar.register({
      ...green,
      requestId: 'boundary-red-deny',
      decisionId: 'boundary-decision-red-deny',
      proposedVersion: '2.0.0-test',
      risk: 'RED',
      redConfirmed: false,
    })
  } catch (e) {
    redDenied = String(e).includes('second Human confirmation')
  }
  if (!redDenied) {
    die(37, 'RED_TWO_STEP_FAIL_CLOSED_BROKEN')
    return
  }
  emit('RED_TWO_STEP_FAIL_CLOSED=PASS')

  const firmwareRoot = path.join(tempRoot, 'vra-registry', 'firmware')
  const registryPath = path.join(firmwareRoot, 'firmware-registry.json')
  const approvalPath = path.join(firmwareRoot, 'signed-approval-records.jsonl')
  const journalPath = path.join(firmwareRoot, 'firmware-registry-journal.jsonl')

  if (!(fs.existsSync(registryPath) && fs.existsSync(approvalPath) && fs.existsSync(journalPath))) {
    die(38, 'DURABLE_FILES_MISSING')
    return
  }
  emit('DURABLE_FILES=PASS')

  const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'))
  if (registry.entries['test.firmware.runtime.boundary']?.version !== '1.0.0-test') {
    die(39, 'REGISTRY_VERSION_INVALID', JSON.stringify(registry))
    return
  }
  emit('REGISTRY_VERSION=PASS')

  const beforeConflictApprovals = readJsonLines(approvalPath).length
  let conflictDenied = false
  try {
    registrar.register({
      ...green,
      requestId: 'boundary-version-conflict',
      decisionId: 'boundary-decision-version-conflict',
      currentVersion: '9.9.9-test',
      proposedVersion: '1.0.2-test',
    })
  } catch (e) {
    conflictDenied = String(e).includes('Firmware Registry version conflict')
  }

  if (!conflictDenied) {
    die(40, 'VERSION_CONFLICT_NOT_DENIED')
    return
  }
  emit('VERSION_CONFLICT_DENIED=PASS')

  const afterConflictApprovals = readJsonLines(approvalPath).length
  emit(`APPROVAL_COUNT_BEFORE_CONFLICT=${beforeConflictApprovals}`)
  emit(`APPROVAL_COUNT_AFTER_CONFLICT=${afterConflictApprovals}`)
  if (afterConflictApprovals !== beforeConflictApprovals) {
    die(41, 'ORPHAN_APPROVAL_ON_VERSION_CONFLICT')
    return
  }
  emit('NO_ORPHAN_APPROVAL_ON_VERSION_CONFLICT=PASS')

  let reject
  try {
    reject = registrar.register({
      requestId: 'boundary-reject-1',
      decision: 'REJECT',
      decisionId: 'boundary-decision-reject-1',
      decidedAt: new Date().toISOString(),
      target: 'test.firmware.runtime.boundary',
      proposedVersion: '2.0.0-test',
      risk: 'AMBER',
      redConfirmed: false,
      source: { actor: 'VERA03', session: 'vera-03', reason: 'runtime reject boundary' },
    })
  } catch (e) {
    die(42, 'REJECT_THROW', String(e))
    return
  }

  if (!(reject.accepted && !reject.committed && reject.registryState === 'REJECTED')) {
    die(43, 'REJECT_RESULT_INVALID', JSON.stringify(reject))
    return
  }
  emit('REJECT=PASS')

  const registryAfterReject = JSON.parse(fs.readFileSync(registryPath, 'utf8'))
  if (registryAfterReject.entries['test.firmware.runtime.boundary']?.version !== '1.0.0-test') {
    die(44, 'REJECT_MUTATED_REGISTRY')
    return
  }
  emit('REJECT_REGISTRY_IMMUTABLE=PASS')

  const journals = readJsonLines(journalPath)
  if (journals.length !== 2) {
    die(45, 'JOURNAL_EVENT_COUNT_INVALID', String(journals.length))
    return
  }
  if (journals[0].event !== 'REGISTRY_COMMIT' || journals[1].event !== 'DECISION_REJECTED') {
    die(46, 'JOURNAL_EVENT_ORDER_INVALID', JSON.stringify(journals))
    return
  }
  if (journals[1].previousHash !== journals[0].entryHash) {
    die(47, 'JOURNAL_HASH_CHAIN_BROKEN')
    return
  }
  emit('JOURNAL_HASH_CHAIN=PASS')

  emit('RUNTIME_BOUNDARY=ALL_PASS')
  process.exitCode = 0
}

app.whenReady()
  .then(main)
  .catch(error => {
    emit(error && error.stack ? error.stack : error)
    process.exitCode = 48
  })
  .finally(() => {
    try { fs.rmSync(tempRoot, { recursive: true, force: true }) } catch {}
    app.quit()
  })
