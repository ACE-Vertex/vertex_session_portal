export const VERA_VXS_HUMAN_AUTHORITY_SCHEMA =
  'vertex-vxs/human-authority-1' as const

export type VeraVxsHumanAuthorityMode = 'LOCKED' | 'FULL'

export interface VeraVxsHumanAuthorityState {
  schema: typeof VERA_VXS_HUMAN_AUTHORITY_SCHEMA
  mode: VeraVxsHumanAuthorityMode
  granted: boolean
  generation: number
  grantedAt: string | null
  grantedBy: 'HUMAN' | null
  scope: 'VERA_FULL_ACCESS'
  persistence: 'PROCESS'
}

let state: VeraVxsHumanAuthorityState = {
  schema: VERA_VXS_HUMAN_AUTHORITY_SCHEMA,
  mode: 'LOCKED',
  granted: false,
  generation: 0,
  grantedAt: null,
  grantedBy: null,
  scope: 'VERA_FULL_ACCESS',
  persistence: 'PROCESS'
}

function snapshot(): VeraVxsHumanAuthorityState {
  return { ...state }
}

export function getVeraVxsHumanAuthorityState(): VeraVxsHumanAuthorityState {
  return snapshot()
}

export function isVeraVxsHumanFullAccessGranted(): boolean {
  return state.granted && state.mode === 'FULL' && state.grantedBy === 'HUMAN'
}

export function grantVeraVxsHumanFullAccess(): VeraVxsHumanAuthorityState {
  state = {
    ...state,
    mode: 'FULL',
    granted: true,
    generation: state.generation + 1,
    grantedAt: new Date().toISOString(),
    grantedBy: 'HUMAN'
  }
  return snapshot()
}

export function revokeVeraVxsHumanFullAccess(): VeraVxsHumanAuthorityState {
  state = {
    ...state,
    mode: 'LOCKED',
    granted: false,
    generation: state.generation + 1,
    grantedAt: null,
    grantedBy: null
  }
  return snapshot()
}

export function toggleVeraVxsHumanFullAccess(): VeraVxsHumanAuthorityState {
  return isVeraVxsHumanFullAccessGranted()
    ? revokeVeraVxsHumanFullAccess()
    : grantVeraVxsHumanFullAccess()
}
