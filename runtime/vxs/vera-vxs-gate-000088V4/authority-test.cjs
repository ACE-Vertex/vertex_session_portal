// src/main/shell/vxs/vera-vxs-human-authority.ts
var VERA_VXS_HUMAN_AUTHORITY_SCHEMA = "vertex-vxs/human-authority-1";
var state = {
  schema: VERA_VXS_HUMAN_AUTHORITY_SCHEMA,
  mode: "LOCKED",
  granted: false,
  generation: 0,
  grantedAt: null,
  grantedBy: null,
  scope: "VERA_FULL_ACCESS",
  persistence: "PROCESS"
};
function snapshot() {
  return { ...state };
}
function getVeraVxsHumanAuthorityState() {
  return snapshot();
}
function isVeraVxsHumanFullAccessGranted() {
  return state.granted && state.mode === "FULL" && state.grantedBy === "HUMAN";
}
function grantVeraVxsHumanFullAccess() {
  state = {
    ...state,
    mode: "FULL",
    granted: true,
    generation: state.generation + 1,
    grantedAt: (/* @__PURE__ */ new Date()).toISOString(),
    grantedBy: "HUMAN"
  };
  return snapshot();
}
function revokeVeraVxsHumanFullAccess() {
  state = {
    ...state,
    mode: "LOCKED",
    granted: false,
    generation: state.generation + 1,
    grantedAt: null,
    grantedBy: null
  };
  return snapshot();
}
function toggleVeraVxsHumanFullAccess() {
  return isVeraVxsHumanFullAccessGranted() ? revokeVeraVxsHumanFullAccess() : grantVeraVxsHumanFullAccess();
}

// scripts/vera_vxs_human_authority_test_000088V4.ts
function ok(value, message) {
  if (!value) throw new Error(message);
}
var initial = getVeraVxsHumanAuthorityState();
ok(initial.mode === "LOCKED", "INITIAL_NOT_LOCKED");
ok(initial.granted === false, "INITIAL_GRANTED");
ok(initial.persistence === "PROCESS", "PERSISTENCE_NOT_PROCESS");
ok(!isVeraVxsHumanFullAccessGranted(), "INITIAL_FULL");
var full = toggleVeraVxsHumanFullAccess();
ok(full.mode === "FULL", "TOGGLE_NOT_FULL");
ok(full.granted === true, "TOGGLE_NOT_GRANTED");
ok(full.grantedBy === "HUMAN", "GRANTER_NOT_HUMAN");
ok(isVeraVxsHumanFullAccessGranted(), "FULL_NOT_ACTIVE");
var locked = toggleVeraVxsHumanFullAccess();
ok(locked.mode === "LOCKED", "TOGGLE_NOT_LOCKED");
ok(!isVeraVxsHumanFullAccessGranted(), "REVOKE_NOT_ACTIVE");
grantVeraVxsHumanFullAccess();
ok(isVeraVxsHumanFullAccessGranted(), "EXPLICIT_GRANT_FAILED");
revokeVeraVxsHumanFullAccess();
ok(!isVeraVxsHumanFullAccessGranted(), "EXPLICIT_REVOKE_FAILED");
console.log("VERA_VXS_HUMAN_AUTHORITY_TEST=PASS");
console.log("DEFAULT_LOCKED=true");
console.log("HUMAN_GRANT_FULL=true");
console.log("HUMAN_REVOKE_LOCKED=true");
console.log("PERSISTENCE=PROCESS");
