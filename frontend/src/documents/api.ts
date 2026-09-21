import type { DocumentRecord, ProcessingStep } from './types'

export const PAGE_SIZE = 20

export function extractionMessage(code: string): string {
  const messages: Record<string, string> = {
    invalid_pdf: 'Le PDF est illisible ou corrompu.',
    encrypted_pdf: 'Ce PDF est chiffré. Importez une version déverrouillée.',
    no_extractable_text:
      'Aucun texte exploitable. Les PDF scannés nécessitent un OCR, encore indisponible.',
  }
  return messages[code] ?? 'L’extraction de ce PDF a échoué.'
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/documents${path}`, init)
  } catch (error) {
    if (init?.signal?.aborted) throw error
    throw new Error(
      'Impossible de joindre le serveur. Vérifiez la connexion puis réessayez.',
      { cause: error },
    )
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail: unknown = body?.detail
    if (typeof detail === 'string') throw new Error(detail)
    if (
      detail &&
      typeof detail === 'object' &&
      'code' in detail &&
      typeof detail.code === 'string'
    ) {
      throw new Error(extractionMessage(detail.code))
    }
    throw new Error(
      response.status === 422
        ? 'Vérifiez les informations saisies.'
        : `La requête a échoué (HTTP ${response.status}).`,
    )
  }
  return response.json() as Promise<T>
}

export const documentsApi = {
  list: (page: number, signal: AbortSignal) =>
    request<DocumentRecord[]>(
      `?limit=${PAGE_SIZE + 1}&offset=${page * PAGE_SIZE}`,
      { signal },
    ),
  get: (id: string, signal?: AbortSignal) =>
    request<DocumentRecord>(`/${id}`, { signal }),
  upload: (title: string, file: File) => {
    const body = new FormData()
    body.set('title', title)
    body.set('file', file)
    return request<DocumentRecord>('/upload', { method: 'POST', body })
  },
  process: (id: string, step: ProcessingStep) =>
    request<DocumentRecord>(`/${id}/${step}`, { method: 'POST' }),
}
