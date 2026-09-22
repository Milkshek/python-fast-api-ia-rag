export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message)
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, init)
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
    const code =
      detail &&
      typeof detail === 'object' &&
      'code' in detail &&
      typeof detail.code === 'string'
        ? detail.code
        : undefined
    const message =
      typeof detail === 'string'
        ? detail
        : response.status === 422
          ? 'Vérifiez les informations saisies.'
          : `La requête a échoué (HTTP ${response.status}).`
    throw new ApiError(message, response.status, code)
  }
  return response.json() as Promise<T>
}
