export type DocumentStatus =
  | 'METADATA_ONLY'
  | 'UPLOADED'
  | 'EXTRACTED'
  | 'CHUNKED'
  | 'INDEXED'
  | 'FAILED'
  | 'DELETING'

export interface DocumentRecord {
  id: string
  title: string
  filename: string
  status: DocumentStatus
  created_at: string
  size_bytes: number | null
  extraction_error: string | null
  embedding_model: string | null
  embedding_dimensions: number | null
}

export type ProcessingStep = 'extract' | 'chunk' | 'index'

export const statusLabels: Record<DocumentStatus, string> = {
  METADATA_ONLY: 'Sans fichier',
  UPLOADED: 'Importé',
  EXTRACTED: 'Texte extrait',
  CHUNKED: 'Passages créés',
  INDEXED: 'Prêt à interroger',
  FAILED: 'Extraction échouée',
  DELETING: 'Suppression en attente',
}
