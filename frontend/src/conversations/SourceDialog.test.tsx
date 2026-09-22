import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  afterAll,
  afterEach,
  beforeAll,
  describe,
  expect,
  it,
  vi,
} from 'vitest'
import { SourceDialog } from './SourceDialog'
import { ExchangeCard } from './ExchangeCard'
import type { ExchangeSource } from './types'

const source: ExchangeSource = {
  id: 1,
  chunk: {
    id: 'chunk-1',
    document_id: 'document-1',
    page_number: 2,
    chunk_index: 1,
    start_offset: 2,
    end_offset: 13,
    text: '48 heures 😀',
  },
}
const page = {
  document_id: 'document-1',
  page_number: 2,
  text: '😀 48 heures 😀 ensuite.',
}
function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }))
}
// jsdom has no native modal dialog methods; behavior is also checked in a real browser.
const dialogMethods = ['showModal', 'close'] as const
const originalMethods = dialogMethods.map((name) =>
  Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, name),
)
beforeAll(() => {
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.open = true
      },
    },
    close: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.open = false
      },
    },
  })
})
afterAll(() => {
  dialogMethods.forEach((name, index) => {
    const original = originalMethods[index]
    if (original)
      Object.defineProperty(HTMLDialogElement.prototype, name, original)
    else Reflect.deleteProperty(HTMLDialogElement.prototype, name)
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Source page', () => {
  it('loads the complete page and highlights offsets counted as Python characters', async () => {
    const fetch = vi.fn(() => json(page))
    vi.stubGlobal('fetch', fetch)
    render(<SourceDialog source={source} onClose={vi.fn()} />)
    expect(
      await screen.findByText('48 heures 😀', { selector: 'mark' }),
    ).toBeInTheDocument()
    expect(screen.getByTestId('page-text')).toHaveTextContent(page.text)
    expect(fetch.mock.calls[0]).toEqual([
      '/api/documents/document-1/pages/2',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    ])
    expect(
      screen.getByRole('link', { name: 'Ouvrir le PDF à cette page' }),
    ).toHaveAttribute('href', '/api/documents/document-1/file#page=2')
    expect(screen.getByRole('link')).toHaveAttribute(
      'rel',
      'noopener noreferrer',
    )
  })

  it('does not highlight a changed page as if it matched the saved citation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json({ ...page, text: 'Un autre contenu.' })),
    )
    render(<SourceDialog source={source} onClose={vi.fn()} />)
    expect(
      await screen.findByText(/La page actuelle diffère/),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('48 heures 😀', { selector: 'mark' }),
    ).not.toBeInTheDocument()
    expect(screen.getByText('Un autre contenu.')).toBeInTheDocument()
  })

  it('shows an error and lets the user retry the page load', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementationOnce(() =>
          json({ detail: 'Document introuvable' }, 404),
        )
        .mockImplementation(() => json(page)),
    )
    const user = userEvent.setup()
    render(<SourceDialog source={source} onClose={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Document introuvable',
    )
    await user.click(screen.getByRole('button', { name: 'Réessayer' }))
    expect(
      await screen.findByText('48 heures 😀', { selector: 'mark' }),
    ).toBeInTheDocument()
  })

  it('closes using its button or the native Escape cancellation', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json(page)),
    )
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<SourceDialog source={source} onClose={onClose} />)
    await user.click(screen.getByRole('button', { name: 'Fermer la source' }))
    expect(onClose).toHaveBeenCalledTimes(1)
    fireEvent(
      screen.getByRole('dialog'),
      new Event('cancel', { bubbles: false }),
    )
    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('aborts a pending page load when closed', async () => {
    let resolve!: (response: Response) => void
    const pending = new Promise<Response>((done) => {
      resolve = done
    })
    const fetch = vi.fn<(url: string, init?: RequestInit) => Promise<Response>>(
      () => pending,
    )
    vi.stubGlobal('fetch', fetch)
    const view = render(<SourceDialog source={source} onClose={vi.fn()} />)
    const signal = fetch.mock.calls[0][1]!.signal!
    view.unmount()
    expect(signal.aborted).toBe(true)
    await act(async () => {
      resolve(await json(page))
    })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it('opens the source from a rendered exchange and closes the dialog', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json(page)),
    )
    const user = userEvent.setup()
    render(
      <ExchangeCard
        exchange={{
          id: 'message-1',
          conversation_id: 'conversation-1',
          sequence: 1,
          question: 'Quel délai ?',
          answer: '48 heures.',
          abstained: false,
          sources: [source],
          created_at: '2026-09-22T10:00:00Z',
        }}
      />,
    )
    await user.click(screen.getByText('Sources utilisées (1)'))
    await user.click(screen.getByRole('button', { name: 'Voir la page 2' }))
    expect(
      await screen.findByText('48 heures 😀', { selector: 'mark' }),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Fermer la source' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
