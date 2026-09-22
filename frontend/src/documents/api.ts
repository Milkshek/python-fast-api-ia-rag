import { ApiError, request as httpRequest } from '../api/client'
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
  try {
    return await httpRequest<T>(`/documents${path}`, init)
  } catch (error) {
    if (error instanceof ApiError && error.code) {
      throw new Error(extractionMessage(error.code), { cause: error })
    }
    throw error
  }
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
