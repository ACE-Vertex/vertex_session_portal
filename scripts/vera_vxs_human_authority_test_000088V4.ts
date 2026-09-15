import {
  getVeraVxsHumanAuthorityState,
  grantVeraVxsHumanFullAccess,
  isVeraVxsHumanFullAccessGranted,
  revokeVeraVxsHumanFullAccess,
  toggleVeraVxsHumanFullAccess
} from '../src/main/shell/vxs/vera-vxs-human-authority'

function ok(value: unknown, message: string): void {
  if (!value) throw new Error(message)
}

const initial = getVeraVxsHumanAuthorityState()
ok(initial.mode === 'LOCKED', 'INITIAL_NOT_LOCKED')
ok(initial.granted === false, 'INITIAL_GRANTED')
ok(initial.persistence === 'PROCESS', 'PERSISTENCE_NOT_PROCESS')
ok(!isVeraVxsHumanFullAccessGranted(), 'INITIAL_FULL')

const full = toggleVeraVxsHumanFullAccess()
ok(full.mode === 'FULL', 'TOGGLE_NOT_FULL')
ok(full.granted === true, 'TOGGLE_NOT_GRANTED')
ok(full.grantedBy === 'HUMAN', 'GRANTER_NOT_HUMAN')
ok(isVeraVxsHumanFullAccessGranted(), 'FULL_NOT_ACTIVE')

const locked = toggleVeraVxsHumanFullAccess()
ok(locked.mode === 'LOCKED', 'TOGGLE_NOT_LOCKED')
ok(!isVeraVxsHumanFullAccessGranted(), 'REVOKE_NOT_ACTIVE')

grantVeraVxsHumanFullAccess()
ok(isVeraVxsHumanFullAccessGranted(), 'EXPLICIT_GRANT_FAILED')
revokeVeraVxsHumanFullAccess()
ok(!isVeraVxsHumanFullAccessGranted(), 'EXPLICIT_REVOKE_FAILED')

console.log('VERA_VXS_HUMAN_AUTHORITY_TEST=PASS')
console.log('DEFAULT_LOCKED=true')
console.log('HUMAN_GRANT_FULL=true')
console.log('HUMAN_REVOKE_LOCKED=true')
console.log('PERSISTENCE=PROCESS')
