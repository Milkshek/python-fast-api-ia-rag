import { useEffect, useRef, useState } from 'react'
import { request } from '../api/client'
import type { ExchangeSource } from './types'

interface DocumentPage {
  document_id: string
  page_number: number
  text: string
}

interface Props {
  source: ExchangeSource
  onClose: () => void
}

export function SourceDialog({ source, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [page, setPage] = useState<DocumentPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  const documentId = source.chunk.document_id
  const pageNumber = source.chunk.page_number

  useEffect(() => {
    const element = dialog.current!
    element.showModal()
    return () => element.close()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    request<DocumentPage>(
      `/documents/${encodeURIComponent(documentId)}/pages/${pageNumber}`,
      { signal: controller.signal },
    )
      .then((result) => {
        if (controller.signal.aborted) return
        setPage(result)
        setError(null)
      })
      .catch((cause: Error) => {
        if (!controller.signal.aborted) setError(cause.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [documentId, pageNumber, revision])

  // Python offsets count Unicode code points; JavaScript slice counts UTF-16 units.
  const characters = page ? Array.from(page.text) : []
  const { start_offset: start, end_offset: end, text } = source.chunk
  const matches =
    page !== null &&
    start >= 0 &&
    end > start &&
    end <= characters.length &&
    characters.slice(start, end).join('') === text

  return (
    <dialog
      className="source-dialog"
      ref={dialog}
      aria-labelledby="source-dialog-title"
      onCancel={onClose}
    >
      <header className="source-dialog-heading">
        <div>
          <span className="eyebrow">DOCUMENT D’ORIGINE</span>
          <h2 id="source-dialog-title">Page {pageNumber}</h2>
        </div>
        <button type="button" onClick={onClose} autoFocus>
          Fermer la source
        </button>
      </header>
      <p className="hint">
        Texte extrait de la page. Le passage cité est mis en évidence lorsqu’il
        correspond à la source enregistrée.
      </p>
      <a
        className="pdf-link"
        href={`/api/documents/${encodeURIComponent(documentId)}/file#page=${pageNumber}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        Ouvrir le PDF à cette page
      </a>
      <p className="hint">
        Le PDF s’ouvre dans un nouvel onglet. Le positionnement sur la page
        dépend du lecteur de votre navigateur.
      </p>
      {loading ? (
        <p role="status">Chargement de la page…</p>
      ) : error ? (
        <div>
          <p role="alert" className="error">
            {error}
          </p>
          <button
            onClick={() => {
              setLoading(true)
              setRevision((value) => value + 1)
            }}
          >
            Réessayer
          </button>
        </div>
      ) : (
        page && (
          <>
            {!matches && (
              <p className="source-warning">
                La page actuelle diffère de la source enregistrée. L’extrait
                original reste consultable dans la réponse.
              </p>
            )}
            {page.text ? (
              <div className="source-page-text" data-testid="page-text">
                {matches ? (
                  <>
                    {characters.slice(0, start).join('')}
                    <mark>{text}</mark>
                    {characters.slice(end).join('')}
                  </>
                ) : (
                  page.text
                )}
              </div>
            ) : (
              <p>Cette page ne contient pas de texte extrait.</p>
            )}
          </>
        )
      )}
    </dialog>
  )
}
