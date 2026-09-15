# CHATGPT WEBVIEW INTERNAL FLEX REPAIR 000039H3H3

Status: verifier-only hotfix.

The runtime H3 repair remains unchanged.

This hotfix fixes the verifier crash caused by Python `subprocess.run(..., text=True)`
decoding `npm.cmd run build` output with the Windows cp932 codec while the build toolchain
can emit UTF-8 bytes.

The verifier now captures raw bytes and decodes only on build failure with an explicit
UTF-8/backslash-replacement path. Successful builds emit only ASCII PASS markers.

Mutation scope:
- verifier script
- this repair note

Runtime Session Portal source/CSS is not modified by H3H3.
