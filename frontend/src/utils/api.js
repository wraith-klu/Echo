/**
 * API utilities for CapsTron backend communication.
 */

/**
 * Normalizes baseUrl to avoid trailing slashes
 */
function cleanUrl(baseUrl) {
  return baseUrl ? baseUrl.replace(/\/+$/, '') : ''
}

export async function pingBackend(baseUrl) {
  const url = `${cleanUrl(baseUrl)}/health`
  const t0 = performance.now()
  const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(5000) })
  const latencyMs = Math.round(performance.now() - t0)

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }

  const data = await response.json()
  return { status: data.status || 'ok', latencyMs }
}

export async function fetchServicesStatus(baseUrl) {
  const url = `${cleanUrl(baseUrl)}/api/v1/status`
  const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(5000) })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  const data = await response.json()
  return data.services || {}
}

export async function transcribeAudio(baseUrl, audioBlob, targetLang, sourceLang) {
  const url = `${cleanUrl(baseUrl)}/api/v1/audio/transcribe`
  const formData = new FormData()

  // Attach WAV file
  formData.append('file', audioBlob, 'recording.wav')
  formData.append('target_language', targetLang)
  if (sourceLang && sourceLang !== 'auto') {
    formData.append('source_language', sourceLang)
  }

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}`
    try {
      const errJson = await response.json()
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson)
    } catch {
      errorDetail = await response.text()
    }
    throw new Error(errorDetail || 'Pipeline request failed')
  }

  const data = await response.json()
  return {
    ...data,
    raw: data,
  }
}

export async function fetchHistory(baseUrl, limit = 20, offset = 0) {
  const url = `${cleanUrl(baseUrl)}/api/v1/history?limit=${limit}&offset=${offset}`
  const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(8000) })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  const data = await response.json()
  return {
    total: data.total ?? data.items?.length ?? 0,
    items: data.items || [],
  }
}

export async function fetchDevices(baseUrl) {
  const url = `${cleanUrl(baseUrl)}/api/v1/devices`
  const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(8000) })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  const data = await response.json()
  return {
    total: data.total ?? data.items?.length ?? 0,
    items: data.items || [],
  }
}

export function getTTSAudioUrl(baseUrl, filename) {
  return `${cleanUrl(baseUrl)}/api/v1/audio/tts/${encodeURIComponent(filename)}`
}
