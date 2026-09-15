# TEST Card RE-RUN Gate 000102V5

`RE-RUN` is rendered only for a VRA whose manifest contains the exact canonical marker
`"card_kind": "TEST"`.

Production/unmarked cards receive no RE-RUN DOM at all. The main process revalidates
the same marker and rejects forged non-TEST requests.

RE-RUN creates a new staged TEST VRA with new artifact/job/correlation/run IDs.
Origin Vera/session/window is preserved. Lane allocation facts are removed.
Human Approval is reset to PENDING and there is no automatic dispatch or Apply.

The existing preload/IPC surface is intentionally unchanged in this pass; the existing
export string transport is used as an internal compatibility tunnel and the trusted main
process interprets only the `vertex-test-rerun:` prefix.

Legacy test cards without `card_kind: TEST` remain fail-closed and show no RE-RUN.
