import { extractionMessage } from './api'
import { statusLabels, type DocumentRecord, type ProcessingStep } from './types'

interface Props {
  document: DocumentRecord | null
  disabled: boolean
  processing: boolean
  onProcess: (step: ProcessingStep) => void
}

const actions: Partial<
  Record<DocumentRecord['status'], { step: ProcessingStep; label: string }>
> = {
  UPLOADED: { step: 'extract', label: 'Extraire le texte' },
  FAILED: { step: 'extract', label: 'Réessayer l’extraction' },
  EXTRACTED: { step: 'chunk', label: 'Découper en passages' },
  CHUNKED: { step: 'index', label: 'Indexer pour la recherche' },
}
const steps = [
  ['Extraction', 'Lire le texte de chaque page.'],
  ['Découpage', 'Créer des passages avec leur position dans le PDF.'],
  ['Indexation', 'Encoder les passages pour la recherche sémantique.'],
]

export function DocumentDetails({
  document,
  disabled,
  processing,
  onProcess,
}: Props) {
  if (!document)
    return (
      <section className="details empty-details">
        <div className="large-file" aria-hidden="true">
          ≡
        </div>
        <span className="eyebrow">DU PDF À LA CONNAISSANCE</span>
        <h2>Un document, trois étapes.</h2>
        <p>
          Sélectionnez un document pour extraire son texte, créer ses passages
          et préparer la recherche.
        </p>
        <div className="mini-pipeline" aria-hidden="true">
          PDF <span>→</span> Texte <span>→</span> Passages <span>→</span> Index
        </div>
      </section>
    )
  const action = actions[document.status]
  const completed =
    (
      { EXTRACTED: 1, CHUNKED: 2, INDEXED: 3 } as Partial<
        Record<DocumentRecord['status'], number>
      >
    )[document.status] ?? 0
  return (
    <section className="details" aria-labelledby="selected-title">
      <div className="detail-heading">
        <span className="eyebrow">DOCUMENT SÉLECTIONNÉ</span>
        <span className={`badge badge-${document.status.toLowerCase()}`}>
          {statusLabels[document.status]}
        </span>
      </div>
      <h2 id="selected-title">{document.title}</h2>
      <p className="filename">{document.filename}</p>
      <dl className="metadata">
        <div>
          <dt>Importé le</dt>
          <dd>{new Date(document.created_at).toLocaleDateString('fr-FR')}</dd>
        </div>
        <div>
          <dt>Taille</dt>
          <dd>
            {document.size_bytes === null
              ? 'Sans fichier'
              : `${(document.size_bytes / 1024).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} Kio`}
          </dd>
        </div>
      </dl>
      <h3>Préparation du document</h3>
      <ol className="pipeline">
        {steps.map(([title, description], index) => (
          <li key={title} className={index < completed ? 'complete' : ''}>
            <span
              className="step-number"
              aria-label={index < completed ? 'Terminé' : 'À faire'}
            >
              {index < completed ? '✓' : index + 1}
            </span>
            <div>
              <strong>{title}</strong>
              <p>{description}</p>
            </div>
          </li>
        ))}
      </ol>
      {document.extraction_error && (
        <p className="error">{extractionMessage(document.extraction_error)}</p>
      )}
      {document.status === 'METADATA_ONLY' && (
        <p>
          Ce document contient uniquement des métadonnées. Importez un PDF pour
          le traiter.
        </p>
      )}
      {document.status === 'DELETING' && (
        <p>
          La suppression de ce document doit être terminée avant toute autre
          opération.
        </p>
      )}
      {document.status === 'CHUNKED' && (
        <p className="hint">
          Cette étape envoie le texte des passages à Gemini et consomme le quota
          de votre compte.
        </p>
      )}
      {document.status === 'INDEXED' && (
        <div className="ready">
          <strong>Votre document est prêt.</strong>
          <p>
            La recherche et les réponses sourcées sont disponibles dans l’API.
            Leur interface arrive à l’étape suivante.
          </p>
        </div>
      )}
      {action && (
        <button
          className="primary"
          disabled={disabled}
          onClick={() => onProcess(action.step)}
        >
          {processing ? 'Traitement en cours…' : action.label}
        </button>
      )}
    </section>
  )
}
