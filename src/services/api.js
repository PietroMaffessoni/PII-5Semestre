import { Capacitor } from '@capacitor/core'

import { clearAuthSession, getAuthToken } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const REQUEST_TIMEOUT_MS = 30000
const SCRIPT_PROMPT_EXAMPLES = [
  'Quero ver o valor faturado por cliente nos últimos 3 meses',
  'Quero analisar o volume de produção por planta no último trimestre',
  'Mostre o valor comprado por fornecedor nos últimos 6 meses',
]

function getApiBaseUrls() {
  return [API_BASE_URL]
}

function buildFetchErrorMessage(baseUrls) {
  const isNativeAndroid = Capacitor.isNativePlatform() && Capacitor.getPlatform() === 'android'
  const triedUrls = `URLs testadas: ${baseUrls.join(', ')}.`

  if (!isNativeAndroid) {
    return `Não foi possível conectar com a API. Verifique se o backend está rodando. ${triedUrls}`
  }

  return `Não foi possível conectar com a API no Android. Verifique se o backend está rodando no computador, se o celular está na mesma rede Wi-Fi e se a porta 8000 está liberada. ${triedUrls}`
}

function buildFriendlyErrorMessage(path, response, payload) {
  const examples = SCRIPT_PROMPT_EXAMPLES
    .map((example) => `"${example}"`)
    .join('; ')

  if (path === '/scripts/generate') {
    if (response.status === 422) {
      return `Não foi possível realizar a busca com esse prompt. Insira um como: ${examples}.`
    }

    if (typeof payload.detail === 'string' && payload.detail.trim()) {
      return payload.detail
    }

    if (payload.detail && typeof payload.detail === 'object') {
      return `Não foi possível realizar a busca com esse prompt. Insira um como: ${examples}.`
    }
  }

  if (typeof payload.detail === 'string' && payload.detail.trim()) {
    return payload.detail
  }

  return 'Não foi possível concluir a solicitação.'
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
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null
    const timeoutId = controller ? setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS) : null

    try {
      response = await fetch(`${baseUrl}${path}`, {
        ...options,
        headers,
        signal: controller?.signal,
      })
      lastError = null
      break
    } catch (error) {
      lastError = error
    } finally {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }
  }

  if (!response) {
    throw new Error(lastError?.message === 'Failed to fetch' || lastError?.name === 'AbortError'
      ? buildFetchErrorMessage(baseUrls)
      : lastError?.message || buildFetchErrorMessage(baseUrls))
  }

  if (response.status === 401) {
    clearAuthSession()
  }

  const payload = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(buildFriendlyErrorMessage(path, response, payload))
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

export function getScriptHistory(options = {}) {
  const params = new URLSearchParams({
    limit: String(options.limit ?? 20),
  })

  return request(`/scripts/history?${params.toString()}`)
}
