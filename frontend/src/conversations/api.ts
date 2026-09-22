import { request } from '../api/client'
import type { Conversation, Exchange } from './types'

export const PAGE_SIZE = 20

export const conversationsApi = {
  list: (documentId: string, page: number, signal: AbortSignal) =>
    request<Conversation[]>(
      `/conversations?document_id=${encodeURIComponent(documentId)}&limit=${PAGE_SIZE + 1}&offset=${page * PAGE_SIZE}`,
      { signal },
    ),
  create: (documentId: string) =>
    request<Conversation>('/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: documentId }),
    }),
  messages: (id: string, page: number, signal: AbortSignal) =>
    request<Exchange[]>(
      `/conversations/${id}/messages?limit=${PAGE_SIZE + 1}&offset=${page * PAGE_SIZE}`,
      { signal },
    ),
  ask: (id: string, question: string) =>
    request<Exchange>(`/conversations/${id}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),
}
