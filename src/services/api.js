import { clearAuthSession, getAuthToken } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const SCRIPT_PROMPT_EXAMPLES = [
  'Quero ver o valor faturado por cliente nos últimos 3 meses',
  'Quero analisar o volume de produção por planta no último trimestre',
  'Mostre o valor comprado por fornecedor nos últimos 6 meses',
]

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

  return 'Não foi possível concluir a requisição.'
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

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  })

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
