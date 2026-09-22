import { useEffect, useState } from 'react'
import { conversationsApi, PAGE_SIZE } from './api'
import { ConversationThread } from './ConversationThread'
import type { Conversation } from './types'

interface Props {
  documentId: string
  disabled?: boolean
  onSendingChange: (sending: boolean) => void
}

export function ConversationPanel({
  documentId,
  disabled = false,
  onSendingChange,
}: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selected, setSelected] = useState<Conversation | null>(null)
  const [page, setPage] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    conversationsApi
      .list(documentId, page, controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return
        setConversations(items.slice(0, PAGE_SIZE))
        setHasNext(items.length > PAGE_SIZE)
        setError(null)
      })
      .catch((cause: Error) => {
        if (!controller.signal.aborted) setError(cause.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [documentId, page, revision])

  function reload(nextPage = page) {
    setLoading(true)
    setPage(nextPage)
    setRevision((value) => value + 1)
  }

  function changeSending(sending: boolean) {
    setBusy(sending)
    onSendingChange(sending)
  }

  async function create() {
    changeSending(true)
    setError(null)
    try {
      const conversation = await conversationsApi.create(documentId)
      setSelected(conversation)
      reload(0)
    } catch (cause) {
      setError((cause as Error).message)
    } finally {
      changeSending(false)
    }
  }

  // A just-created or selected conversation stays available outside the current list page.
  const options =
    selected && !conversations.some((item) => item.id === selected.id)
      ? [selected, ...conversations]
      : conversations
  return (
    <section className="conversations" aria-labelledby="conversations-title">
      <div className="conversation-heading">
        <div>
          <span className="eyebrow">INTERROGER LE DOCUMENT</span>
          <h2 id="conversations-title">Conversations</h2>
        </div>
        <button
          disabled={disabled || busy || loading}
          onClick={() => void create()}
        >
          Nouvelle conversation
        </button>
      </div>
      <p className="hint">
        Vos échanges et leurs sources sont enregistrés. Envoyer une question
        utilise Gemini.
      </p>
      {loading && <p role="status">Chargement des conversations…</p>}
      {error && (
        <div>
          <p className="error" role="alert">
            {error}
          </p>
          <button
            disabled={disabled || busy || loading}
            onClick={() => reload()}
          >
            Recharger les conversations
          </button>
        </div>
      )}
      {!loading && !error && !options.length && (
        <p>Aucune conversation pour ce document.</p>
      )}
      {options.length > 0 && (
        <div className="conversation-picker">
          <label htmlFor="conversation-select">Conversation</label>
          <select
            id="conversation-select"
            value={selected?.id ?? ''}
            disabled={disabled || busy || loading}
            onChange={(event) =>
              setSelected(
                options.find((item) => item.id === event.target.value) ?? null,
              )
            }
          >
            <option value="">Choisir une conversation</option>
            {options.map((item) => (
              <option key={item.id} value={item.id}>
                Conversation du{' '}
                {new Date(item.created_at).toLocaleString('fr-FR')}
              </option>
            ))}
          </select>
        </div>
      )}
      {(page > 0 || hasNext) && (
        <nav className="pagination" aria-label="Pages des conversations">
          <button
            disabled={disabled || busy || loading || page === 0}
            onClick={() => reload(page - 1)}
          >
            Conversations récentes
          </button>
          <span>Page {page + 1}</span>
          <button
            disabled={disabled || busy || loading || !hasNext}
            onClick={() => reload(page + 1)}
          >
            Conversations anciennes
          </button>
        </nav>
      )}
      {selected && (
        <ConversationThread
          key={selected.id}
          conversationId={selected.id}
          disabled={disabled || busy}
          onSendingChange={changeSending}
        />
      )}
    </section>
  )
}
