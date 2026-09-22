import { useEffect, useState, type FormEvent } from 'react'
import { conversationsApi, PAGE_SIZE } from './api'
import { ExchangeCard } from './ExchangeCard'
import type { Exchange } from './types'

interface Props {
  conversationId: string
  disabled: boolean
  onSendingChange: (sending: boolean) => void
}

export function ConversationThread({
  conversationId,
  disabled,
  onSendingChange,
}: Props) {
  const [messages, setMessages] = useState<Exchange[]>([])
  const [page, setPage] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sendError, setSendError] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [sending, setSending] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    conversationsApi
      .messages(conversationId, page, controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return
        setMessages(items.slice(0, PAGE_SIZE))
        setHasNext(items.length > PAGE_SIZE)
        setLoadError(null)
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setLoadError(error.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [conversationId, page, revision])

  function reload(nextPage = page) {
    setLoading(true)
    setPage(nextPage)
    setRevision((value) => value + 1)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = question.trim()
    if (!text || disabled || loading || sending) return
    setSending(true)
    onSendingChange(true)
    setSendError(null)
    try {
      const exchange = await conversationsApi.ask(conversationId, text)
      setQuestion('')
      reload(Math.floor((exchange.sequence - 1) / PAGE_SIZE))
    } catch (error) {
      setSendError((error as Error).message)
    } finally {
      setSending(false)
      onSendingChange(false)
    }
  }

  return (
    <div className="conversation-thread">
      <div className="history-heading">
        <h3>Échanges enregistrés</h3>
        <button
          className="text-button"
          disabled={disabled || loading || sending}
          onClick={() => reload()}
        >
          Recharger les échanges
        </button>
      </div>
      {loading ? (
        <p role="status">Chargement des échanges…</p>
      ) : loadError ? (
        <p className="error" role="alert">
          {loadError}
        </p>
      ) : messages.length ? (
        messages.map((message) => (
          <ExchangeCard key={message.id} exchange={message} />
        ))
      ) : (
        <p className="hint">Posez votre première question à ce document.</p>
      )}
      {(page > 0 || hasNext) && (
        <nav className="pagination" aria-label="Pages des échanges">
          <button
            disabled={disabled || loading || sending || page === 0}
            onClick={() => reload(page - 1)}
          >
            Échanges précédents
          </button>
          <span>Page {page + 1}</span>
          <button
            disabled={disabled || loading || sending || !hasNext}
            onClick={() => reload(page + 1)}
          >
            Échanges suivants
          </button>
        </nav>
      )}
      <form className="question-form" onSubmit={submit}>
        <label htmlFor="conversation-question">Votre question</label>
        <textarea
          id="conversation-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          maxLength={2000}
          rows={3}
          required
          disabled={disabled || sending || loading || loadError !== null}
          placeholder="Ex. Quel est le délai de réponse ?"
        />
        <p className="hint">
          Chaque question est traitée indépendamment. Précisez son sujet, même
          s’il apparaît dans un échange précédent.
        </p>
        {sendError && (
          <div className="error" role="alert">
            <p>{sendError}</p>
            <p>
              En cas de connexion interrompue, rechargez les échanges avant de
              renvoyer la question : la réponse peut avoir été enregistrée.
            </p>
          </div>
        )}
        {sending && (
          <p role="status">
            Recherche des passages et rédaction de la réponse…
          </p>
        )}
        <button
          className="primary"
          type="submit"
          disabled={
            disabled ||
            sending ||
            loading ||
            loadError !== null ||
            !question.trim()
          }
        >
          {sending ? 'Réponse en cours…' : 'Envoyer la question'}
        </button>
      </form>
    </div>
  )
}
