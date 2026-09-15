# VXS VSH Prefix Runtime Repair 000007H1

## Problem

New Host-rendered system lines can still appear as:

`VSH │ ...`

even though the embedded shell identity is now VXS.

The current Host Bridge owns the legacy prefix inside its private Shadow DOM
append closure. Replacing the whole Host Bridge would risk overwriting newer
production work.

## Repair

The current VXS Service installs a synchronous `textContent` normalizer on the
existing output element.

Every Host assignment to `.output.textContent` is normalized immediately:

- `VSH │` -> `VXS │`
- `VSH ›` -> `VXS ›`
- `VERTEX SHELL 000080V4G · SHELL N` -> `VXS 0.1.0 · SHELL N`

This occurs at the assignment boundary rather than one animation frame later,
so command echo, stream output and RESULT lines never need to remain visibly
branded as VSH.

## Fail-closed verification

VERIFY confirms that the *current production Host Bridge* still contains the
legacy system-prefix anchor:

`kind === 'system' ? 'VSH │ '`

and its append pipeline before accepting this repair.

Host Bridge itself is not copied or replaced.

## Preserved

- VXS 0.1.0
- settings / editor modes / font size
- Shell tab close
- Command Registry
- Workspace Detector
- vxs --version / --help / status / doctor
- PowerShell compatibility
- Human Gate / HUMAN_APPLY
- Workstation authority
- vra/1
