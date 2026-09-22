export interface Conversation {
  id: string
  document_id: string
  created_at: string
}

export interface ExchangeSource {
  id: number
  chunk: {
    id: string
    document_id: string
    page_number: number
    chunk_index: number
    start_offset: number
    end_offset: number
    text: string
  }
}

export interface Exchange {
  id: string
  conversation_id: string
  sequence: number
  question: string
  answer: string
  abstained: boolean
  sources: ExchangeSource[]
  created_at: string
}
