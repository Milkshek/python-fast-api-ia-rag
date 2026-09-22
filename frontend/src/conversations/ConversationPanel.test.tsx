import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ConversationPanel } from './ConversationPanel'

const conversation = {
  id: 'conversation-1',
  document_id: 'document-1',
  created_at: '2026-09-22T09:00:00Z',
}
const exchange = {
  id: 'message-1',
  conversation_id: conversation.id,
  sequence: 1,
  question: 'Quel délai ?',
  answer: 'Le délai est de 48 heures.',
  abstained: false,
  created_at: '2026-09-22T09:01:00Z',
  sources: [
    {
      id: 1,
      chunk: {
        id: 'chunk-1',
        document_id: 'document-1',
        page_number: 2,
        chunk_index: 1,
        start_offset: 0,
        end_offset: 22,
        text: 'Réponse sous 48 heures.',
      },
    },
  ],
}
function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }))
}
afterEach(() => vi.unstubAllGlobals())

async function openConversation() {
  const user = userEvent.setup()
  await user.selectOptions(
    await screen.findByLabelText('Conversation'),
    conversation.id,
  )
  return user
}

describe('Conversations', () => {
  it('creates a conversation only after an explicit click', async () => {
    const fetch = vi.fn((_url: string, init?: RequestInit) =>
      json(init?.method === 'POST' ? conversation : []),
    )
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(
      <ConversationPanel documentId="document-1" onSendingChange={vi.fn()} />,
    )
    await screen.findByText('Aucune conversation pour ce document.')
    expect(fetch.mock.calls.every(([, init]) => init?.method !== 'POST')).toBe(
      true,
    )
    await user.click(
      screen.getByRole('button', { name: 'Nouvelle conversation' }),
    )
    expect(await screen.findByLabelText('Votre question')).toBeInTheDocument()
    const create = fetch.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(JSON.parse(create![1]!.body as string)).toEqual({
      document_id: 'document-1',
    })
  })

  it('reloads persisted questions, answers and source excerpts', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        json(url.includes('/messages') ? [exchange] : [conversation]),
      ),
    )
    render(
      <ConversationPanel documentId="document-1" onSendingChange={vi.fn()} />,
    )
    await openConversation()
    expect(
      await screen.findByText('Le délai est de 48 heures.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Quel délai ?')).toBeInTheDocument()
    expect(screen.getByText('Page 2')).toBeInTheDocument()
    expect(screen.getByText('Réponse sous 48 heures.')).toBeInTheDocument()
  })

  it('sends a question then displays the saved response', async () => {
    let sent = false
    const fetch = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === 'POST') {
        sent = true
        return json(exchange, 201)
      }
      return json(
        url.includes('/messages') ? (sent ? [exchange] : []) : [conversation],
      )
    })
    vi.stubGlobal('fetch', fetch)
    render(
      <ConversationPanel documentId="document-1" onSendingChange={vi.fn()} />,
    )
    const user = await openConversation()
    await user.type(
      await screen.findByLabelText('Votre question'),
      'Quel délai ?',
    )
    await user.click(
      screen.getByRole('button', { name: 'Envoyer la question' }),
    )
    expect(
      await screen.findByText('Le délai est de 48 heures.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Votre question')).toHaveValue('')
    expect(
      fetch.mock.calls.some(
        ([url, init]) =>
          url.endsWith('/messages') &&
          init?.body === JSON.stringify({ question: 'Quel délai ?' }),
      ),
    ).toBe(true)
  })

  it('keeps the question and releases controls after a quota error', async () => {
    const onSending = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) =>
        init?.method === 'POST'
          ? json({ detail: 'Quota Gemini atteint' }, 429)
          : json(url.includes('/messages') ? [] : [conversation]),
      ),
    )
    render(
      <ConversationPanel documentId="document-1" onSendingChange={onSending} />,
    )
    const user = await openConversation()
    await user.type(
      await screen.findByLabelText('Votre question'),
      'Quel délai ?',
    )
    await user.click(
      screen.getByRole('button', { name: 'Envoyer la question' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Quota Gemini atteint',
    )
    expect(screen.getByLabelText('Votre question')).toHaveValue('Quel délai ?')
    expect(
      screen.getByRole('button', { name: 'Envoyer la question' }),
    ).toBeEnabled()
    expect(onSending.mock.calls.map(([value]) => value)).toEqual([true, false])
  })

  it('retries loading history without sending a question', async () => {
    let fail = true
    const fetch = vi.fn((url: string) => {
      if (!url.includes('/messages')) return json([conversation])
      if (fail) {
        fail = false
        return Promise.reject(new TypeError('network'))
      }
      return json([exchange])
    })
    vi.stubGlobal('fetch', fetch)
    render(
      <ConversationPanel documentId="document-1" onSendingChange={vi.fn()} />,
    )
    await openConversation()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossible de joindre',
    )
    fireEvent.click(
      screen.getByRole('button', { name: 'Recharger les échanges' }),
    )
    expect(
      await screen.findByText('Le délai est de 48 heures.'),
    ).toBeInTheDocument()
  })
  it('ignores an obsolete history response after switching conversation', async () => {
    const other = { ...conversation, id: 'conversation-2' }
    let resolveOld!: (response: Response) => void
    const pending = new Promise<Response>((resolve) => {
      resolveOld = resolve
    })
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/conversation-1/messages')) return pending
        if (url.includes('/conversation-2/messages'))
          return json([
            {
              ...exchange,
              id: 'message-2',
              question: 'Nouvelle question',
              answer: 'Nouvelle réponse',
            },
          ])
        return json([conversation, other])
      }),
    )
    render(
      <ConversationPanel documentId="document-1" onSendingChange={vi.fn()} />,
    )
    const user = await openConversation()
    await user.selectOptions(screen.getByLabelText('Conversation'), other.id)
    expect(await screen.findByText('Nouvelle réponse')).toBeInTheDocument()
    await act(async () => {
      resolveOld(await json([exchange]))
    })
    expect(
      screen.queryByText('Le délai est de 48 heures.'),
    ).not.toBeInTheDocument()
    expect(screen.getByText('Nouvelle réponse')).toBeInTheDocument()
  })

  it('paginates exchanges and displays an abstention without inventing a source', async () => {
    const items = Array.from({ length: 21 }, (_, index) => ({
      ...exchange,
      id: `message-${index}`,
      sequence: index + 1,
    }))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (!url.includes('/messages')) return json([conversation])
        return json(
          url.includes('offset=20')
            ? [
                {
                  ...items[20],
                  answer: 'Les passages sont insuffisants.',
                  abstained: true,
                  sources: [],
                },
              ]
            : items,
        )
      }),
    )
    render(
      <ConversationPanel documentId="document-1" onSendingChange={vi.fn()} />,
    )
    const user = await openConversation()
    await user.click(
      await screen.findByRole('button', { name: 'Échanges suivants' }),
    )
    expect(
      await screen.findByText('Les passages sont insuffisants.'),
    ).toBeInTheDocument()
    expect(screen.getByText('Information insuffisante')).toBeInTheDocument()
    expect(screen.queryByText(/Sources utilisées/)).not.toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Échanges suivants' }),
    ).toBeDisabled()
  })

  it('locks conversation changes during generation', async () => {
    let resolveSend!: (response: Response) => void
    const pending = new Promise<Response>((resolve) => {
      resolveSend = resolve
    })
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) =>
        init?.method === 'POST'
          ? pending
          : json(url.includes('/messages') ? [] : [conversation]),
      ),
    )
    const onSending = vi.fn()
    render(
      <ConversationPanel documentId="document-1" onSendingChange={onSending} />,
    )
    const user = await openConversation()
    await user.type(
      await screen.findByLabelText('Votre question'),
      'Quel délai ?',
    )
    await user.click(
      screen.getByRole('button', { name: 'Envoyer la question' }),
    )
    expect(screen.getByLabelText('Conversation')).toBeDisabled()
    expect(screen.getByLabelText('Votre question')).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Nouvelle conversation' }),
    ).toBeDisabled()
    expect(onSending).toHaveBeenLastCalledWith(true)
    await act(async () => {
      resolveSend(await json({ detail: 'Gemini indisponible' }, 503))
    })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Gemini indisponible',
    )
    expect(screen.getByLabelText('Conversation')).toBeEnabled()
    expect(onSending).toHaveBeenLastCalledWith(false)
  })
  it('blocks the existing question while a new conversation is being created', async () => {
    let resolveCreate!: (response: Response) => void
    const pending = new Promise<Response>((resolve) => {
      resolveCreate = resolve
    })
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) =>
        init?.method === 'POST'
          ? pending
          : json(url.includes('/messages') ? [] : [conversation]),
      ),
    )
    render(
      <ConversationPanel documentId="document-1" onSendingChange={vi.fn()} />,
    )
    const user = await openConversation()
    await user.type(
      await screen.findByLabelText('Votre question'),
      'Quel délai ?',
    )
    await user.click(
      screen.getByRole('button', { name: 'Nouvelle conversation' }),
    )
    expect(screen.getByLabelText('Votre question')).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Envoyer la question' }),
    ).toBeDisabled()
    await act(async () => {
      resolveCreate(await json({ detail: 'Indisponible' }, 503))
    })
    expect(screen.getByLabelText('Votre question')).toBeEnabled()
  })
  it('honors a parent operation lock for both creation and the current question', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        json(url.includes('/messages') ? [] : [conversation]),
      ),
    )
    const onSending = vi.fn()
    const view = render(
      <ConversationPanel documentId="document-1" onSendingChange={onSending} />,
    )
    const user = await openConversation()
    await user.type(
      await screen.findByLabelText('Votre question'),
      'Quel délai ?',
    )
    view.rerender(
      <ConversationPanel
        documentId="document-1"
        onSendingChange={onSending}
        disabled
      />,
    )
    expect(screen.getByLabelText('Votre question')).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Envoyer la question' }),
    ).toBeDisabled()
    expect(
      screen.getByRole('button', { name: 'Nouvelle conversation' }),
    ).toBeDisabled()
    expect(screen.getByLabelText('Conversation')).toBeDisabled()
  })
})
