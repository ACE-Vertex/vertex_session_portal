# Workstation Dispatch Pipeline Probe 000074V5

Read-only diagnostic for:

- Artifact: `vertex-session-portal-final-ux-wordmark-autofit-000073V5`
- Job: `job-vera05-session-portal-final-ux-wordmark-autofit-000073V5`

It checks, without POST/mutation:

1. 127.0.0.1:47832 listener PID / executable / command line
2. `GET /v1/health`
3. `GET /v1/safety`
4. `GET /v1/jobs/job-vera05-session-portal-final-ux-wordmark-autofit-000073V5`
5. `GET /v1/jobs/job-vera05-session-portal-final-ux-wordmark-autofit-000073V5/evidence`
6. `_incoming` final VRA + `.meta.json`
7. latest persistent registry generation
8. durable runtime JSON files containing the job/artifact id

The script emits a deterministic `CLASSIFICATION` line.

No Workstation or Portal runtime state is modified.
