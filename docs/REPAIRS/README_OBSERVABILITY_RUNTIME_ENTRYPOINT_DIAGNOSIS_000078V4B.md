# Observability Runtime Entrypoint Diagnosis 000078V4B

Diagnoses why Observability Core 000078V4 is installed/verified in source but
no runtime Black Box appears after a full Session Portal restart.

It inspects source entrypoint markers, package.json main/scripts, Electron/Vite
config anchors, live process command lines, built JS/CJS/MJS marker presence,
Event Ray marker presence, and packaged app.asar candidates.

No production source, process, build artifact, Event Ray, or Black Box is
modified by the diagnostic runner.
