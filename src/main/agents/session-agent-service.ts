import type {
  RetrievalHit,
  SessionAgentTurn,
  SessionChatMessage,
  SessionAgentRequest,
  SessionProviderStatus,
  SessionContextAttachment,
  SessionContextScope,
  AiLaneId,
  ListAiLaneModelsRequest,
  SaveAiLaneSettingsRequest
} from '../../shared/contracts'
import {
  LocalRetrievalService
} from '../retrieval/local-retrieval-service'
import {
  ConfiguredProvider,
  type ProviderMessage
} from '../providers/configured-provider'
import {
  ProviderSettingsStore,
  sessionLaneId
} from '../providers/provider-settings-store'
import {
  SessionAgentStore
} from './session-agent-store'

export class SessionAgentService {
  constructor(
    private readonly store:
      SessionAgentStore,
    private readonly retrieval:
      LocalRetrievalService,
    private readonly providerSettings:
      ProviderSettingsStore,
    private readonly provider:
      ConfiguredProvider =
        new ConfiguredProvider(providerSettings)
  ) {}

  providerStatus():
    Promise<SessionProviderStatus> {
    return this.provider.status()
  }

  getProviderSettings() {
    return this.providerSettings.get()
  }

  saveProviderSettings(request: import('../../shared/contracts').SaveProviderSettingsRequest) {
    return this.providerSettings.save(request)
  }

  clearProviderApiKey() {
    return this.providerSettings.clearApiKey()
  }

  getAiLaneSettings() {
    return this.providerSettings.getAiLaneSettings()
  }

  saveAiLaneSettings(request: SaveAiLaneSettingsRequest) {
    return this.providerSettings.saveLane(request)
  }

  clearAiLaneApiKey(laneId: AiLaneId) {
    return this.providerSettings.clearLaneApiKey(laneId)
  }

  listAiLaneModels(request: ListAiLaneModelsRequest): Promise<string[]> {
    return this.provider.listModels(request)
  }

  conversation(
    sessionId: string
  ): SessionChatMessage[] {
    this.store.getSession(
      sessionId
    )

    return this.store
      .listMessages(
        sessionId,
        40
      )
  }

  retrievalHits(
    sessionId: string
  ): RetrievalHit[] {
    return this.store
      .getLatestRetrieval(
        sessionId
      )
  }

  async send(
    request:
      SessionAgentRequest
  ): Promise<SessionAgentTurn> {
    const session =
      this.store.getSession(
        request.sessionId
      )

    const projection =
      this.store
        .getActiveProjection(
          session.id
        )

    const previous =
      this.store.listMessages(
        session.id,
        14
      )

    const contextScope: SessionContextScope =
      request.contextScope ??
      (session.kind === 'SEARCH' ? 'PROJECT_EVIDENCE' : 'SESSION')

    const retrieval =
      contextScope === 'SESSION'
        ? []
        : this.retrieval.search(request.body, 8).filter(hit => {
            if (contextScope === 'PROJECT') return hit.source === 'PROJECT'
            if (contextScope === 'EVIDENCE') return hit.source === 'EVIDENCE'
            return true
          })

    const attachments = this.normalizeAttachments(request.attachments)

    const system =
      this.buildSystemPrompt(
        session.title,
        session.kind,
        projection
      )

    const incoming =
      projection
        ? this.store
            .getIncomingHandoffs(
              projection.missionId,
              session.id
            )
        : []

    const handoffContext =
      incoming.length > 0
        ? [
            '',
            'Typed incoming handoffs:',
            ...incoming
              .reverse()
              .map(
                (handoff) =>
                  `[${handoff.kind}] from ${handoff.fromSessionId}: ${handoff.body}`
              )
          ].join('\n')
        : ''

    const retrievalContext =
      retrieval.length > 0
        ? [
            '',
            `Read-only local retrieval evidence (scope ${contextScope}):`,
            ...retrieval.map(
              (
                hit,
                index
              ) => [
                `SOURCE ${index + 1}: ${hit.source} ${hit.relativePath}:${hit.lineStart}-${hit.lineEnd}`,
                hit.snippet
              ].join('\n')
            ),
            '',
            'Use only the supplied retrieval evidence for claims about local project/evidence content. If it is insufficient, say so.'
          ].join('\n')
        : (
            contextScope !== 'SESSION'
              ? [
                  '',
                  `No matching local retrieval hit was found for scope ${contextScope}. Do not invent local source content.`
                ].join('\n')
              : ''
          )

    const attachmentContext =
      attachments.length > 0
        ? [
            '',
            'User-selected local context attachments:',
            ...attachments.map((attachment, index) => [
              `ATTACHMENT ${index + 1}: ${attachment.name}`,
              `PATH: ${attachment.path}`,
              attachment.content
            ].join('\n')),
            '',
            'Treat attached text as user-supplied context. Do not claim the file was modified or executed.'
          ].join('\n')
        : ''

    const providerMessages:
      ProviderMessage[] = [
        {
          role: 'system',
          content:
            `${system}${handoffContext}${retrievalContext}${attachmentContext}`
        },
        ...previous.map(
          (message):
            ProviderMessage => ({
              role:
                message.role ===
                  'USER'
                  ? 'user'
                  : 'assistant',
              content:
                message.body
            })
        ),
        {
          role: 'user',
          content:
            request.body.trim()
        }
      ]

    const user =
      this.store.appendMessage(
        session.id,
        'USER',
        request.body
      )

    if (
      session.kind === 'SEARCH'
    ) {
      this.store.replaceLatestRetrieval(
        session.id,
        user.id,
        retrieval
      )
    }

    const laneId = sessionLaneId(session.id)
    const result =
      await this.provider.chat(
        providerMessages,
        laneId ?? undefined
      )

    const assistant =
      this.store.appendMessage(
        session.id,
        'ASSISTANT',
        result.content
      )

    return {
      sessionId:
        session.id,
      provider: result.provider,
      model:
        result.model,
      user,
      assistant,
      retrieval
    }
  }

  private normalizeAttachments(
    attachments: SessionContextAttachment[] | undefined
  ): SessionContextAttachment[] {
    if (!Array.isArray(attachments)) return []

    return attachments.slice(0, 5).map((attachment, index) => {
      const name = typeof attachment?.name === 'string' ? attachment.name.trim() : ''
      const path = typeof attachment?.path === 'string' ? attachment.path.trim() : ''
      const content = typeof attachment?.content === 'string' ? attachment.content : ''

      if (!name || !path) throw new Error(`SESSION_CONTEXT_ATTACHMENT_${index + 1}_INVALID`)
      if (content.length > 262144) throw new Error(`SESSION_CONTEXT_ATTACHMENT_${index + 1}_TOO_LARGE`)

      return { name, path, content }
    })
  }

  private buildSystemPrompt(
    title: string,
    kind: string,
    projection:
      | {
          objective: string
          role: string
          brief: string
        }
      | null
  ): string {
    const lines = [
      `You are ${title}, an independent Vera session inside VERTEX Session Portal.`,
      'Keep this session context isolated from other Vera sessions unless a typed handoff is explicitly provided.',
      'Do not claim you executed tools, files, UI actions, database mutations, or external sends unless the supplied context explicitly says so.'
    ]

    if (kind === 'SEARCH') {
      lines.push(
        'Your specialization is read-only retrieval, source finding, archive navigation and evidence support.',
        'PROJECT and EVIDENCE adapters may supply concrete local source snippets.',
        'VCR and VCA are backed by the local Workstation SQLite layer and are exposed through the Session Portal Explorer; PROJECT/EVIDENCE retrieval remains a separate read-only adapter.'
      )
    }

    if (projection) {
      lines.push(
        `Current Virtual ARD role: ${projection.role}.`,
        `Mission objective: ${projection.objective}`,
        `Role brief: ${projection.brief}`
      )
    } else {
      lines.push(
        'No Virtual ARD role is currently projected onto this session.'
      )
    }

    return lines.join('\n')
  }
}
