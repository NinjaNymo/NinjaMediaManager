// API client for backend communication

const API_BASE = '/api'

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// Files API
export const filesApi = {
  browse: (path: string = '') =>
    fetchApi<import('../types/api').BrowseResponse>(`/files/browse?path=${encodeURIComponent(path)}`),

  browseOutput: (path: string = '') =>
    fetchApi<import('../types/api').BrowseResponse>(`/files/browse-output?path=${encodeURIComponent(path)}`),

  scan: (path: string = '', recursive: boolean = true) =>
    fetchApi<{ path: string; count: number; files: { name: string; path: string; size: number }[] }>(
      `/files/scan?path=${encodeURIComponent(path)}&recursive=${recursive}`
    ),
}

// Media API
export const mediaApi = {
  getInfo: (path: string) =>
    fetchApi<import('../types/api').MediaInfoResponse>(`/media/info?path=${encodeURIComponent(path)}`),

  getTracks: (path: string, trackType?: string) => {
    let url = `/media/tracks?path=${encodeURIComponent(path)}`
    if (trackType) url += `&track_type=${trackType}`
    return fetchApi<{ path: string; tracks: import('../types/api').Track[] }>(url)
  },
}

// Subtitles API
export const subtitlesApi = {
  extract: (request: import('../types/api').ExtractRequest) =>
    fetchApi<import('../types/api').ExtractResponse>('/subtitles/extract', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  ocr: (request: import('../types/api').OCRRequest) =>
    fetchApi<import('../types/api').OCRResponse>('/subtitles/ocr', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  downloadUrl: (filepath: string) => `${API_BASE}/subtitles/download/${encodeURIComponent(filepath)}`,

  getInfo: (path: string) =>
    fetchApi<import('../types/api').SubtitleInfoResponse>(`/subtitles/info?path=${encodeURIComponent(path)}`),

  spellCheck: (path: string, options: {
    replacementsEnabled: boolean
    replacements: string
    ignoreEnabled: boolean
    ignoreList: string
    language: string
  }) =>
    fetchApi<import('../types/api').SpellCheckResponse>('/subtitles/spell-check', {
      method: 'POST',
      body: JSON.stringify({
        path,
        replacements_enabled: options.replacementsEnabled,
        replacements: options.replacements,
        ignore_enabled: options.ignoreEnabled,
        ignore_list: options.ignoreList,
        language: options.language,
      }),
    }),

  getPgsImage: (path: string, index: number) =>
    fetchApi<import('../types/api').PgsImageResponse>(
      `/subtitles/pgs-image?path=${encodeURIComponent(path)}&index=${index}`
    ),

  editSubtitle: (path: string, index: number, newText: string) =>
    fetchApi<import('../types/api').SubtitleEditResponse>('/subtitles/edit', {
      method: 'POST',
      body: JSON.stringify({
        path,
        index,
        new_text: newText,
      }),
    }),

  checkStampCollision: (path: string, startTime: string, endTime: string) =>
    fetchApi<import('../types/api').CheckStampCollisionResponse>(
      `/subtitles/check-stamp-collision?path=${encodeURIComponent(path)}&start_time=${encodeURIComponent(startTime)}&end_time=${encodeURIComponent(endTime)}`
    ),

  addStamp: (request: import('../types/api').AddStampRequest) =>
    fetchApi<import('../types/api').AddStampResponse>('/subtitles/add-stamp', {
      method: 'POST',
      body: JSON.stringify(request),
    }),
}

// Health API
export const healthApi = {
  check: () => fetchApi<import('../types/api').HealthResponse>('/health'),
}
