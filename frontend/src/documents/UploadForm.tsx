import { useState, type FormEvent } from 'react'

interface Props {
  disabled: boolean
  onUpload: (title: string, file: File) => Promise<boolean>
}

export function UploadForm({ disabled, onUpload }: Props) {
  const [error, setError] = useState<string | null>(null)
  const [file, setFile] = useState<File | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const data = new FormData(form)
    const title = String(data.get('title') ?? '').trim()
    if (!title || !file || file.size === 0) {
      setError('Ajoutez un titre et un fichier PDF non vide.')
      return
    }
    if (file.size > 10 * 1024 * 1024) {
      setError('Le PDF doit faire au maximum 10 Mio.')
      return
    }
    setError(null)
    if (await onUpload(title, file)) {
      form.reset()
      setFile(null)
    }
  }

  return (
    <form className="upload-form" onSubmit={submit}>
      <div className="section-heading">
        <span className="eyebrow">NOUVEAU DOCUMENT</span>
        <h2>Ajouter un PDF</h2>
      </div>
      <label htmlFor="document-title">Titre du document</label>
      <input
        id="document-title"
        name="title"
        placeholder="Ex. Contrat de prestation"
        maxLength={200}
        required
        disabled={disabled}
      />
      <label htmlFor="document-file">Fichier PDF</label>
      <input
        id="document-file"
        name="file"
        type="file"
        accept="application/pdf,.pdf"
        onChange={(event) => setFile(event.currentTarget.files?.[0] ?? null)}
        required
        disabled={disabled}
      />
      <p className="hint">10 Mio maximum · PDF contenant du texte</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button className="primary" disabled={disabled} type="submit">
        Importer le PDF
      </button>
    </form>
  )
}
