import { request as httpRequest } from 'node:http'

export const WORKSTATION_HTTP = Object.freeze({
  host: '127.0.0.1',
  port: 47832,
  baseUrl: 'http://127.0.0.1:47832',
  timeoutMs: 2500
})

export type WorkstationJson = Record<string, unknown>

export interface RegisterJobHttpRequest {
  artifact_filename: string
  artifact_sha256: string
}

export interface EvidenceAckHttpRequest {
  evidence_id: string
  artifact_id: string
  returned_at: string
}

export type WorkstationSafetyActionHttp = 'DRAIN' | 'ESTOP' | 'RESET' | 'RESUME'

export interface SafetyActionHttpRequest {
  request_id: string
  authority: 'HUMAN'
  reason: string
}

export interface WorkstationHttpResult<T extends WorkstationJson = WorkstationJson> {
  status: number
  body: T
}

export class WorkstationHttpError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string
  ) {
    super(message)
    this.name = 'WorkstationHttpError'
  }
}

export class WorkstationClient {
  health(): Promise<WorkstationHttpResult> {
    return this.jsonRequest('GET', '/v1/health')
  }

  registerJob(payload: RegisterJobHttpRequest): Promise<WorkstationHttpResult> {
    return this.jsonRequest('POST', '/v1/jobs', payload)
  }

  getJob(jobId: string): Promise<WorkstationHttpResult> {
    return this.jsonRequest('GET', `/v1/jobs/${this.jobPath(jobId)}`)
  }

  getEvidence(jobId: string): Promise<WorkstationHttpResult> {
    return this.jsonRequest('GET', `/v1/jobs/${this.jobPath(jobId)}/evidence`)
  }

  acknowledgeEvidence(jobId: string, payload: EvidenceAckHttpRequest): Promise<WorkstationHttpResult> {
    return this.jsonRequest('POST', `/v1/jobs/${this.jobPath(jobId)}/evidence/ack`, payload)
  }

  getSafety(): Promise<WorkstationHttpResult> {
    return this.jsonRequest('GET', '/v1/safety')
  }

  safetyAction(
    action: WorkstationSafetyActionHttp,
    payload: SafetyActionHttpRequest
  ): Promise<WorkstationHttpResult> {
    const path = this.safetyPath(action)
    return this.jsonRequest('POST', path, payload)
  }

  private safetyPath(action: WorkstationSafetyActionHttp): string {
    switch (action) {
      case 'DRAIN': return '/v1/safety/drain'
      case 'ESTOP': return '/v1/safety/estop'
      case 'RESET': return '/v1/safety/reset'
      case 'RESUME': return '/v1/safety/resume'
    }
  }

  private jobPath(jobId: string): string {
    const value = jobId.trim()
    if (!value || value.includes('/') || value.includes('\\')) {
      throw new Error('WORKSTATION_JOB_ID_PATH_REJECTED')
    }
    return encodeURIComponent(value)
  }

  private jsonRequest(
    method: 'GET' | 'POST',
    path: string,
    payload?: unknown
  ): Promise<WorkstationHttpResult> {
    if (!path.startsWith('/v1/')) {
      return Promise.reject(new Error('WORKSTATION_HTTP_NON_V1_PATH_REJECTED'))
    }

    const body = payload ? Buffer.from(JSON.stringify(payload), 'utf8') : Buffer.alloc(0)
    return new Promise((resolve, reject) => {
      const req = httpRequest({
        host: WORKSTATION_HTTP.host,
        port: WORKSTATION_HTTP.port,
        method,
        path,
        timeout: WORKSTATION_HTTP.timeoutMs,
        headers: {
          Accept: 'application/json',
          ...(body.length > 0
            ? {
                'Content-Type': 'application/json',
                'Content-Length': String(body.length)
              }
            : {})
        }
      }, response => {
        const chunks: Buffer[] = []
        response.on('data', chunk => chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)))
        response.on('end', () => {
          const raw = Buffer.concat(chunks).toString('utf8')
          let parsed: WorkstationJson = {}
          if (raw.trim()) {
            try {
              const value = JSON.parse(raw) as unknown
              parsed = value && typeof value === 'object' && !Array.isArray(value)
                ? value as WorkstationJson
                : { value }
            } catch {
              reject(new Error('WORKSTATION_HTTP_INVALID_JSON_RESPONSE'))
              return
            }
          }
          const status = response.statusCode ?? 0
          if (status < 200 || status >= 300) {
            const error = parsed.error
            const record = error && typeof error === 'object' && !Array.isArray(error)
              ? error as Record<string, unknown>
              : {}
            const code = typeof record.code === 'string' ? record.code : `HTTP_${status}`
            const message = typeof record.message === 'string' ? record.message : `Workstation HTTP ${status}`
            reject(new WorkstationHttpError(status, code, message))
            return
          }
          resolve({ status, body: parsed })
        })
      })
      req.on('timeout', () => req.destroy(new Error('WORKSTATION_HTTP_TIMEOUT')))
      req.on('error', reject)
      if (body.length > 0) req.write(body)
      req.end()
    })
  }
}
