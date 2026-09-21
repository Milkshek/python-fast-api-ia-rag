import { statusLabels, type DocumentRecord } from './types'

interface Props {
  documents: DocumentRecord[]
  selectedId?: string
  disabled: boolean
  onSelect: (document: DocumentRecord) => void
}

export function DocumentList({
  documents,
  selectedId,
  disabled,
  onSelect,
}: Props) {
  if (!documents.length)
    return (
      <div className="empty-library">
        <span aria-hidden="true">＋</span>
        <h3>Votre bibliothèque est vide</h3>
        <p>Importez un PDF pour commencer à explorer son contenu.</p>
      </div>
    )
  return (
    <ul className="document-list">
      {documents.map((document) => (
        <li key={document.id}>
          <button
            className={`document-row ${document.id === selectedId ? 'selected' : ''}`}
            aria-pressed={document.id === selectedId}
            disabled={disabled}
            onClick={() => onSelect(document)}
          >
            <span className="file-icon" aria-hidden="true">
              PDF
            </span>
            <span className="document-info">
              <strong>{document.title}</strong>
              <span>{document.filename}</span>
              <span className={`badge badge-${document.status.toLowerCase()}`}>
                {statusLabels[document.status]}
              </span>
            </span>
            <span aria-hidden="true">↗</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
