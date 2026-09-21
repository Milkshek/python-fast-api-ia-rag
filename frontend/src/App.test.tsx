import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const document = {
  id: 'doc-1',
  title: 'Contrat de démonstration',
  filename: 'contrat.pdf',
  status: 'UPLOADED',
  created_at: '2026-09-21T10:00:00Z',
  size_bytes: 1200,
  extraction_error: null,
  embedding_model: null,
  embedding_dimensions: null,
}

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }))
}

afterEach(() => vi.unstubAllGlobals())

describe('Documents', () => {
  it('shows an empty library and an accessible upload form', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json([])),
    )
    render(<App />)
    expect(
      await screen.findByText('Votre bibliothèque est vide'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Titre du document')).toBeInTheDocument()
    expect(screen.getByLabelText('Fichier PDF')).toBeInTheDocument()
  })

  it('selects a document and updates its status after extraction', async () => {
    const fetch = vi.fn((_url: string, init?: RequestInit) => {
      if (init?.method === 'POST')
        return json({ ...document, status: 'EXTRACTED' })
      return json([document])
    })
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await user.click(
      await screen.findByRole('button', { name: /Contrat de démonstration/ }),
    )
    await user.click(screen.getByRole('button', { name: 'Extraire le texte' }))
    expect(
      await screen.findByRole('button', { name: 'Découper en passages' }),
    ).toBeInTheDocument()
    expect(
      fetch.mock.calls.some(
        ([url, init]) => url.endsWith('/extract') && init?.method === 'POST',
      ),
    ).toBe(true)
  })

  it('preserves the chunked status when Gemini quota prevents indexing', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) =>
        init?.method === 'POST'
          ? json({ detail: 'Quota Gemini atteint ; réessayer plus tard' }, 429)
          : json([{ ...document, status: 'CHUNKED' }]),
      ),
    )
    const user = userEvent.setup()
    render(<App />)
    await user.click(
      await screen.findByRole('button', { name: /Contrat de démonstration/ }),
    )
    await user.click(
      screen.getByRole('button', { name: 'Indexer pour la recherche' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Quota Gemini atteint',
    )
    expect(
      screen.getByRole('button', { name: 'Indexer pour la recherche' }),
    ).toBeEnabled()
  })

  it('uploads the chosen file as multipart and selects the returned document', async () => {
    const fetch = vi.fn((_url: string, init?: RequestInit) =>
      init?.method === 'POST' ? json(document, 201) : json([]),
    )
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('Votre bibliothèque est vide')
    await user.type(
      screen.getByLabelText('Titre du document'),
      'Contrat de démonstration',
    )
    await user.upload(
      screen.getByLabelText('Fichier PDF'),
      new File(['%PDF-test'], 'contrat.pdf', { type: 'application/pdf' }),
    )
    expect(screen.getByLabelText('Titre du document')).toHaveValue(
      'Contrat de démonstration',
    )
    expect(
      (screen.getByLabelText('Fichier PDF') as HTMLInputElement).files?.length,
    ).toBe(1)
    // jsdom does not reflect user-event's file list in native required validation.
    fireEvent.submit(
      screen.getByRole('button', { name: 'Importer le PDF' }).closest('form')!,
    )
    expect(
      await screen.findByRole('button', { name: 'Extraire le texte' }),
    ).toBeInTheDocument()
    const call = fetch.mock.calls.find(([url]) => url.endsWith('/upload'))
    expect(call?.[1]?.body).toBeInstanceOf(FormData)
    expect((call?.[1]?.body as FormData).get('title')).toBe(
      'Contrat de démonstration',
    )
  })

  it('shows a retry action when the library is unavailable', async () => {
    const fetch = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('network'))
      .mockImplementation(() => json([]))
    vi.stubGlobal('fetch', fetch)
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Impossible de joindre',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Réessayer' }))
    await waitFor(() =>
      expect(
        screen.getByText('Votre bibliothèque est vide'),
      ).toBeInTheDocument(),
    )
  })
  it('refreshes a failed extraction and explains why the PDF cannot be read', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (init?.method === 'POST')
          return json({ detail: { code: 'no_extractable_text' } }, 422)
        if (url.endsWith('/doc-1'))
          return json({
            ...document,
            status: 'FAILED',
            extraction_error: 'no_extractable_text',
          })
        return json([document])
      }),
    )
    const user = userEvent.setup()
    render(<App />)
    await user.click(
      await screen.findByRole('button', { name: /Contrat de démonstration/ }),
    )
    await user.click(screen.getByRole('button', { name: 'Extraire le texte' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Aucun texte exploitable',
    )
    expect(
      screen.getByRole('button', { name: 'Réessayer l’extraction' }),
    ).toBeEnabled()
  })

  it('requests the next page without dropping the extra lookahead document', async () => {
    const records = Array.from({ length: 21 }, (_, i) => ({
      ...document,
      id: `doc-${i}`,
      title: `Document ${i}`,
    }))
    const fetch = vi.fn((url: string) =>
      json(url.includes('offset=20') ? [records[20]] : records),
    )
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: 'Suivante' }))
    expect(
      await screen.findByRole('button', { name: /Document 20/ }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Suivante' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Précédente' })).toBeEnabled()
    expect(fetch.mock.calls[1][0]).toContain('limit=21&offset=20')
  })
  it('runs each processing step and displays the final indexed state', async () => {
    const statuses: Record<string, string> = {
      extract: 'EXTRACTED',
      chunk: 'CHUNKED',
      index: 'INDEXED',
    }
    const fetch = vi.fn((url: string, init?: RequestInit) =>
      init?.method === 'POST'
        ? json({ ...document, status: statuses[url.split('/').at(-1)!] })
        : json([document]),
    )
    vi.stubGlobal('fetch', fetch)
    const user = userEvent.setup()
    render(<App />)
    await user.click(
      await screen.findByRole('button', { name: /Contrat de démonstration/ }),
    )
    for (const label of [
      'Extraire le texte',
      'Découper en passages',
      'Indexer pour la recherche',
    ]) {
      await user.click(await screen.findByRole('button', { name: label }))
    }
    expect(
      await screen.findByText('Votre document est prêt.'),
    ).toBeInTheDocument()
    expect(
      fetch.mock.calls
        .filter(([, init]) => init?.method === 'POST')
        .map(([url]) => url),
    ).toEqual([
      '/api/documents/doc-1/extract',
      '/api/documents/doc-1/chunk',
      '/api/documents/doc-1/index',
    ])
  })

  it('locks conflicting actions during indexing and releases them after an error', async () => {
    let resolveIndex!: (response: Response) => void
    const pending = new Promise<Response>((resolve) => {
      resolveIndex = resolve
    })
    const records = Array.from({ length: 21 }, (_, i) => ({
      ...document,
      id: `doc-${i}`,
      title: `Document ${i}`,
      status: 'CHUNKED',
    }))
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) =>
        init?.method === 'POST' ? pending : json(records),
      ),
    )
    const user = userEvent.setup()
    render(<App />)
    await user.click(await screen.findByRole('button', { name: /Document 0/ }))
    await user.click(
      screen.getByRole('button', { name: 'Indexer pour la recherche' }),
    )
    for (const label of [
      'Importer le PDF',
      'Suivante',
      'Actualiser',
      'Traitement en cours…',
    ]) {
      expect(screen.getByRole('button', { name: label })).toBeDisabled()
    }
    expect(screen.getByLabelText('Titre du document')).toBeDisabled()
    expect(screen.getByRole('button', { name: /Document 19/ })).toBeDisabled()
    resolveIndex(
      new Response(JSON.stringify({ detail: 'Gemini indisponible' }), {
        status: 503,
      }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Gemini indisponible',
    )
    expect(
      screen.getByRole('button', { name: 'Indexer pour la recherche' }),
    ).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Suivante' })).toBeEnabled()
    expect(screen.getByLabelText('Titre du document')).toBeEnabled()
  })
})
