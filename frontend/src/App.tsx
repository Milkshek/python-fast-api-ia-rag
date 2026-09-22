import { useEffect, useState } from 'react'
import { ConversationPanel } from './conversations/ConversationPanel'
import { documentsApi, PAGE_SIZE } from './documents/api'
import { DocumentDetails } from './documents/DocumentDetails'
import { DocumentList } from './documents/DocumentList'
import { UploadForm } from './documents/UploadForm'
import type { DocumentRecord, ProcessingStep } from './documents/types'

export default function App() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [selected, setSelected] = useState<DocumentRecord | null>(null)
  const [page, setPage] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<'upload' | 'process' | null>(null)
  const [listError, setListError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [asking, setAsking] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    documentsApi
      .list(page, controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return
        setDocuments(items.slice(0, PAGE_SIZE))
        setHasNext(items.length > PAGE_SIZE)
        setListError(null)
      })
      .catch((cause: Error) => {
        if (!controller.signal.aborted) setListError(cause.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [page, revision])

  function reload(nextPage = page) {
    setLoading(true)
    setSelected(null)
    setError(null)
    setPage(nextPage)
    setRevision((value) => value + 1)
  }

  function updateDocument(document: DocumentRecord) {
    setSelected(document)
    setDocuments((items) =>
      items.map((item) => (item.id === document.id ? document : item)),
    )
  }

  async function upload(title: string, file: File) {
    setBusy('upload')
    setError(null)
    try {
      const document = await documentsApi.upload(title, file)
      setSelected(document)
      setLoading(true)
      setRevision((value) => value + 1)
      return true
    } catch (cause) {
      setError((cause as Error).message)
      return false
    } finally {
      setBusy(null)
    }
  }

  async function process(step: ProcessingStep) {
    if (!selected) return
    setBusy('process')
    setError(null)
    try {
      updateDocument(await documentsApi.process(selected.id, step))
    } catch (cause) {
      // Extraction can persist FAILED before returning an HTTP error.
      if (step === 'extract') {
        try {
          updateDocument(await documentsApi.get(selected.id))
        } catch {
          /* Keep the original operation error. */
        }
      }
      setError((cause as Error).message)
    } finally {
      setBusy(null)
    }
  }

  const disabled = loading || busy !== null || asking
  return (
    <>
      <header className="site-header">
        <a
          className="brand"
          href="/"
          aria-label="Document Intelligence, accueil"
        >
          <span aria-hidden="true">d.</span>Document Intelligence
        </a>
        <span className="workspace-label">ESPACE DOCUMENTAIRE</span>
      </header>
      <main>
        <div className="intro">
          <span className="eyebrow">VOTRE BIBLIOTHÈQUE</span>
          <h1>
            Des documents.
            <br />
            <span>Des connaissances à explorer.</span>
          </h1>
          <p>
            Importez vos PDF et préparez leur contenu pour des réponses
            sourcées.
          </p>
        </div>
        <div className="workspace">
          <aside className="library" aria-label="Bibliothèque de documents">
            <UploadForm disabled={disabled} onUpload={upload} />
            <div className="library-heading">
              <h2>Mes documents</h2>
              <button
                className="text-button"
                disabled={disabled}
                onClick={() => reload()}
              >
                Actualiser
              </button>
            </div>
            {loading && (
              <p role="status" className="loading">
                Chargement des documents…
              </p>
            )}
            {listError ? (
              <div className="list-error">
                <p role="alert" className="error">
                  {listError}
                </p>
                <button disabled={disabled} onClick={() => reload()}>
                  Réessayer
                </button>
              </div>
            ) : (
              !loading && (
                <DocumentList
                  documents={documents}
                  selectedId={selected?.id}
                  disabled={disabled}
                  onSelect={(document) => {
                    setSelected(document)
                    setError(null)
                  }}
                />
              )
            )}
            {(page > 0 || hasNext) && (
              <nav className="pagination" aria-label="Pages des documents">
                <button
                  disabled={disabled || page === 0}
                  onClick={() => reload(page - 1)}
                >
                  Précédente
                </button>
                <span>Page {page + 1}</span>
                <button
                  disabled={disabled || !hasNext}
                  onClick={() => reload(page + 1)}
                >
                  Suivante
                </button>
              </nav>
            )}
          </aside>
          <div className="detail-column">
            {busy && (
              <p role="status" className="operation-status">
                {busy === 'upload'
                  ? 'Import du PDF en cours…'
                  : 'Traitement en cours. Vous pouvez suivre le résultat ici.'}
              </p>
            )}
            {error && (
              <p role="alert" className="error operation-error">
                {error}
              </p>
            )}
            <DocumentDetails
              document={selected}
              disabled={disabled}
              processing={busy === 'process'}
              onProcess={(step) => void process(step)}
            />
            {selected?.status === 'INDEXED' && (
              <ConversationPanel
                key={selected.id}
                documentId={selected.id}
                disabled={disabled}
                onSendingChange={setAsking}
              />
            )}
            <p className="workspace-note">
              Chaque étape est lancée à votre demande. Vos sources restent liées
              au document d’origine.
            </p>
          </div>
        </div>
      </main>
      <footer>
        Document Intelligence <span>PDF → Texte → Passages → Recherche</span>
      </footer>
    </>
  )
}
