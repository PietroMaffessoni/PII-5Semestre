import { Capacitor } from '@capacitor/core'

import { clearAuthSession, getAuthToken } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const DEFAULT_ANDROID_EMULATOR_API_URL = 'http://10.0.2.2:8000/api/v1'

function getApiBaseUrls() {
  const urls = [API_BASE_URL]
  const isNativeAndroid = Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'

  if (!isNativeAndroid) {
    return urls
  }

  if (!urls.includes(DEFAULT_ANDROID_EMULATOR_API_URL)) {
    urls.push(DEFAULT_ANDROID_EMULATOR_API_URL)
  }

  try {
    const normalized = new URL(API_BASE_URL)

    if (normalized.hostname === 'localhost' || normalized.hostname === '127.0.0.1') {
      normalized.hostname = '10.0.2.2'
      const emulatorUrl = normalized.toString().replace(/\/$/, '')

      if (!urls.includes(emulatorUrl)) {
        urls.unshift(emulatorUrl)
      }
    }
  } catch {
    // Ignore invalid custom URLs and keep the configured fallback list.
  }

  return urls
}

function buildFetchErrorMessage(baseUrls) {
  const isNativeAndroid = Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'
  const emulatorHint = 'No emulador, use http://10.0.2.2:8000/api/v1.'
  const deviceHint = 'No celular fisico, use o IP do seu PC na rede, por exemplo http://192.168.0.10:8000/api/v1.'
  const triedUrls = `URLs testadas: ${baseUrls.join(', ')}.`

  if (!isNativeAndroid) {
    return `Nao foi possivel conectar com a API. Verifique se o backend esta rodando. ${triedUrls}`
  }

  return `Nao foi possivel conectar com a API no Android. Verifique se o backend esta rodando, se o app foi sincronizado apos mudar o .env e se a URL da API esta correta. ${emulatorHint} ${deviceHint} ${triedUrls}`
}

async function request(path, options = {}) {
  const token = getAuthToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const baseUrls = getApiBaseUrls()
  let response
  let lastError = null

  for (const baseUrl of baseUrls) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        ...options,
        headers,
      })
      lastError = null
      break
    } catch (error) {
      lastError = error
    }
  }

  if (!response) {
    throw new Error(lastError?.message === 'Failed to fetch'
      ? buildFetchErrorMessage(baseUrls)
      : lastError?.message || buildFetchErrorMessage(baseUrls))
  }

  if (response.status === 401) {
    clearAuthSession()
  }

  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(payload.detail || 'Nao foi possivel concluir a requisicao.')
  }

  return payload
}

export function login(credentials) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
}

export function getAuthenticatedUser() {
  return request('/auth/me')
}

export function generateScript(question, options = {}) {
  return request('/scripts/generate', {
    method: 'POST',
    body: JSON.stringify({
      question,
      execute: options.execute ?? true,
      preview_limit: options.previewLimit ?? 20,
    }),
  })
}
