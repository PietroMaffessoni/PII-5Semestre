import { clearAuthSession, getAuthToken, getStoredAuth } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === 'true'

function buildMockPreview(question) {
  const normalized = question.toLowerCase()

  if (normalized.includes('compra') || normalized.includes('fornecedor')) {
    return {
      interpretation: {
        domain: 'compras',
        metric: 'valor_comprado',
        dimensions: ['fornecedor', 'mes'],
        period_months: 3,
        filters: ['periodo: ultimos meses solicitados', 'agrupar por fornecedor'],
        chart_suggestion: 'colunas agrupadas',
      },
      suggested_tables: ['EKKO', 'EKPO'],
      relevant_fields: [
        { table: 'EKKO', field: 'LIFNR', label: 'fornecedor', description: 'Codigo do fornecedor' },
        { table: 'EKKO', field: 'BEDAT', label: 'mes', description: 'Data do documento de compras' },
        { table: 'EKPO', field: 'NETWR', label: 'valor_comprado', description: 'Valor do item do pedido' },
      ],
      join_suggestions: ['JOIN entre EKKO e EKPO por EBELN.'],
      suggested_filters: ['periodo: ultimos meses solicitados', 'agrupar por fornecedor'],
      draft_script:
        '-- SQL inicial gerado em modo local\nSELECT\n  ekko.LIFNR AS fornecedor,\n  DATE_TRUNC(\'month\', ekko.BEDAT) AS mes,\n  SUM(ekpo.NETWR) AS valor_comprado\nFROM EKKO ekko\nJOIN EKPO ekpo ON ekko.EBELN = ekpo.EBELN\nWHERE ekko.BEDAT >= CURRENT_DATE - INTERVAL \'3 months\'\nGROUP BY ekko.LIFNR, DATE_TRUNC(\'month\', ekko.BEDAT)\nORDER BY ekko.LIFNR, DATE_TRUNC(\'month\', ekko.BEDAT);',
      preview_rows: [
        { fornecedor: 'F0001', mes: '2026-02-01', valor_comprado: 128500.25 },
        { fornecedor: 'F0001', mes: '2026-03-01', valor_comprado: 119300.8 },
        { fornecedor: 'F0002', mes: '2026-04-01', valor_comprado: 143920.1 },
      ],
    }
  }

  if (normalized.includes('fatur') || normalized.includes('cliente')) {
    return {
      interpretation: {
        domain: 'faturamento',
        metric: 'valor_faturado',
        dimensions: ['cliente', 'mes'],
        period_months: 3,
        filters: ['periodo: ultimos meses solicitados', 'agrupar por cliente'],
        chart_suggestion: 'colunas agrupadas',
      },
      suggested_tables: ['VBRK', 'VBRP'],
      relevant_fields: [
        { table: 'VBRK', field: 'KUNNR', label: 'cliente', description: 'Codigo do cliente' },
        { table: 'VBRK', field: 'FKDAT', label: 'mes', description: 'Data de faturamento' },
        { table: 'VBRP', field: 'NETWR', label: 'valor_faturado', description: 'Valor faturado do item' },
      ],
      join_suggestions: ['JOIN entre VBRK e VBRP por VBELN.'],
      suggested_filters: ['periodo: ultimos meses solicitados', 'agrupar por cliente'],
      draft_script:
        '-- SQL inicial gerado em modo local\nSELECT\n  vbrk.KUNNR AS cliente,\n  DATE_TRUNC(\'month\', vbrk.FKDAT) AS mes,\n  SUM(vbrp.NETWR) AS valor_faturado\nFROM VBRK vbrk\nJOIN VBRP vbrp ON vbrk.VBELN = vbrp.VBELN\nWHERE vbrk.FKDAT >= CURRENT_DATE - INTERVAL \'3 months\'\nGROUP BY vbrk.KUNNR, DATE_TRUNC(\'month\', vbrk.FKDAT)\nORDER BY vbrk.KUNNR, DATE_TRUNC(\'month\', vbrk.FKDAT);',
      preview_rows: [
        { cliente: 'C0001', mes: '2026-02-01', valor_faturado: 210500.9 },
        { cliente: 'C0002', mes: '2026-03-01', valor_faturado: 189320.45 },
        { cliente: 'C0003', mes: '2026-04-01', valor_faturado: 241180.6 },
      ],
    }
  }

  return {
    interpretation: {
      domain: 'producao',
      metric: 'volume_producao',
      dimensions: ['planta', 'mes'],
      period_months: 3,
      filters: ['periodo: ultimos meses solicitados', 'agrupar por planta'],
      chart_suggestion: 'barras mensais',
    },
    suggested_tables: ['AFKO'],
    relevant_fields: [
      { table: 'AFKO', field: 'WERKS', label: 'planta', description: 'Centro produtivo' },
      { table: 'AFKO', field: 'GSTRP', label: 'mes', description: 'Data basica de inicio' },
      { table: 'AFKO', field: 'GAMNG', label: 'volume_producao', description: 'Quantidade total da ordem' },
    ],
    join_suggestions: ['Consulta simples em tabela unica.'],
    suggested_filters: ['periodo: ultimos meses solicitados', 'agrupar por planta'],
    draft_script:
      '-- SQL inicial gerado em modo local\nSELECT\n  afko.WERKS AS planta,\n  DATE_TRUNC(\'month\', afko.GSTRP) AS mes,\n  SUM(afko.GAMNG) AS volume_producao\nFROM AFKO afko\nWHERE afko.GSTRP >= CURRENT_DATE - INTERVAL \'3 months\'\nGROUP BY afko.WERKS, DATE_TRUNC(\'month\', afko.GSTRP)\nORDER BY afko.WERKS, DATE_TRUNC(\'month\', afko.GSTRP);',
    preview_rows: [
      { planta: '1000', mes: '2026-02-01', volume_producao: 1480 },
      { planta: '1000', mes: '2026-03-01', volume_producao: 1635 },
      { planta: '2000', mes: '2026-04-01', volume_producao: 1710 },
    ],
  }
}

async function mockRequest(path, options = {}) {
  const method = options.method || 'GET'

  if (path === '/auth/login' && method === 'POST') {
    const payload = JSON.parse(options.body || '{}')
    const usuario = payload.usuario?.trim() || 'demo'

    return {
      token: 'mock-token',
      user: {
        id: 1,
        usuario,
        role: 'admin',
      },
    }
  }

  if (path === '/auth/me') {
    const session = getStoredAuth()
    if (!session?.user) {
      throw new Error('Autenticacao obrigatoria.')
    }

    return { user: session.user }
  }

  if (path === '/scripts/generate' && method === 'POST') {
    const payload = JSON.parse(options.body || '{}')
    const session = getStoredAuth()

    if (!session?.user) {
      throw new Error('Autenticacao obrigatoria.')
    }

    const preview = buildMockPreview(payload.question || '')
    return {
      question: payload.question,
      context: null,
      status: 'draft',
      retrieval_mode: 'mock',
      requested_by: session.user.usuario,
      preview_rows: preview.preview_rows,
      preview_row_count: preview.preview_rows.length,
      interpretation: preview.interpretation,
      suggested_tables: preview.suggested_tables,
      relevant_fields: preview.relevant_fields,
      join_suggestions: preview.join_suggestions,
      suggested_filters: preview.suggested_filters,
      draft_script: preview.draft_script,
    }
  }

  throw new Error(`Rota mock nao implementada: ${method} ${path}`)
}

async function request(path, options = {}) {
  if (USE_MOCK_API) {
    return mockRequest(path, options)
  }

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
