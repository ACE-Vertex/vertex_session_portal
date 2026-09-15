# VXS Agent Context Capability Pack 000021

Adds:

- `vxs context`
- `vxs context --json`

The command creates one bounded, safe development-context snapshot suitable for
humans or agent/LLM handoff.

Included:
- host/runtime identity
- detected workspace identity and markers
- package manager/framework/script summary
- Git branch and up to 120 changed-status rows
- VXS process memory/uptime
- Workstation listener observation on 127.0.0.1:47832
- development tool versions
- up to 12 recent durable Jobs
- up to 8 recent failed Jobs

Explicitly excluded:
- secret environment variable values
- full log bodies
- file contents
- credentials
- filesystem mutation
- network mutation

JSON schema identifier: `vxs-agent-context/1`.
