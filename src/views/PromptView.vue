<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

import { generateScript, getAuthenticatedUser, getScriptHistory } from '../services/api'
import { clearAuthSession, getCurrentUser } from '../services/auth'

const router = useRouter()
const prompt = ref('')
const result = ref(null)
const errorMessage = ref('')
const isLoading = ref(false)
const isCheckingAuth = ref(true)
const currentUser = ref(getCurrentUser())
const chartElement = ref(null)
const historyItems = ref([])
const isLoadingHistory = ref(false)
const selectedHistoryId = ref(null)
const historyCollapsed = ref(false)
const selectedMonths = ref([])
const theme = ref(document.documentElement.dataset.theme || 'light')
let chartInstance = null

const welcomeLabel = computed(() => currentUser.value?.usuario || 'usuário autenticado')
const currentRole = computed(() => currentUser.value?.role || '')
const isAdmin = computed(() => currentRole.value === 'admin')
const canViewAllHistory = computed(() => ['admin', 'gerente'].includes(currentRole.value))
const hasUsableInterpretation = computed(() => Boolean(result.value?.is_understood))
const previewColumns = computed(() => {
  if (!result.value?.preview_rows?.length) {
    return []
  }

  return Object.keys(result.value.preview_rows[0])
})
const monthOptions = computed(() => {
  if (!result.value?.preview_rows?.length || !previewColumns.value.includes('mes')) {
    return []
  }

  const uniqueValues = [...new Set(result.value.preview_rows.map((row) => String(row.mes)))]
    .sort((left, right) => left.localeCompare(right))

  return uniqueValues.map((value) => ({
    value,
    label: formatPreviewValue('mes', value),
  }))
})
const filteredPreviewRows = computed(() => {
  const rows = result.value?.preview_rows || []
  if (!rows.length || !previewColumns.value.includes('mes')) {
    return rows
  }

  if (!selectedMonths.value.length) {
    return []
  }

  const allowed = new Set(selectedMonths.value)
  return rows.filter((row) => allowed.has(String(row.mes)))
})
const chartConfig = computed(() => buildLocalChartPayload(filteredPreviewRows.value))
const chartTypeLabel = computed(() => {
  const chartType = chartConfig.value?.chart_type

  if (chartType === 'line') {
    return 'linhas'
  }

  if (chartType === 'grouped_bar') {
    return 'barras agrupadas'
  }

  if (chartType === 'horizontal_bar') {
    return 'barras horizontais'
  }

  return 'barras'
})
const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
})
const compactNumberFormatter = new Intl.NumberFormat('pt-BR', {
  notation: 'compact',
  maximumFractionDigits: 1,
})
const monthLabels = {
  '01': 'Janeiro',
  '02': 'Fevereiro',
  '03': 'Março',
  '04': 'Abril',
  '05': 'Maio',
  '06': 'Junho',
  '07': 'Julho',
  '08': 'Agosto',
  '09': 'Setembro',
  '10': 'Outubro',
  '11': 'Novembro',
  '12': 'Dezembro',
}

function formatPreviewValue(column, value) {
  if (value === null || value === undefined) {
    return ''
  }

  if (column === 'mes') {
    const match = String(value).match(/^(\d{4})-(\d{2})-/)
    if (match) {
      const [, , month] = match
      return monthLabels[month] || value
    }
  }

  if (column === 'valor_faturado') {
    const numericValue = Number(value)
    if (!Number.isNaN(numericValue)) {
      return currencyFormatter.format(numericValue)
    }
  }

  return value
}

function buildLocalChartPayload(rows) {
  if (!rows?.length) {
    return null
  }

  const columns = Object.keys(rows[0])
  const numericColumns = columns.filter((column) =>
    rows.every((row) => row[column] !== null && row[column] !== undefined && !Number.isNaN(Number(row[column])))
  )
  const dimensionColumns = columns.filter((column) => !numericColumns.includes(column))
  const categoryColumn = dimensionColumns.includes('mes') ? 'mes' : dimensionColumns[0]
  const valueColumn = numericColumns[0]
  const seriesColumn = dimensionColumns.find((column) => column !== categoryColumn) || null

  if (!categoryColumn || !valueColumn) {
    return result.value?.chart_payload || null
  }

  const categoryValues = categoryColumn === 'mes'
    ? [...new Set(rows.map((row) => String(row[categoryColumn])))]
      .sort((left, right) => left.localeCompare(right))
    : [...new Set(rows.map((row) => String(row[categoryColumn])))]

  const labels = categoryValues.map((value) => {
    if (categoryColumn === 'mes') {
      const match = value.match(/^(\d{4})-(\d{2})-/)
      if (match) {
        return ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][Number(match[2]) - 1]
      }
    }
    return value
  })

  const series = seriesColumn
    ? [...new Set(rows.map((row) => String(row[seriesColumn])))]
      .map((seriesName) => ({
        name: seriesName,
        data: categoryValues.map((categoryValue) => {
          const row = rows.find(
            (item) => String(item[seriesColumn]) === seriesName && String(item[categoryColumn]) === categoryValue
          )
          return row ? Number(row[valueColumn]) : null
        }),
      }))
    : [
        {
          name: valueColumn,
          data: categoryValues.map((categoryValue) => {
            const row = rows.find((item) => String(item[categoryColumn]) === categoryValue)
            return row ? Number(row[valueColumn]) : 0
          }),
        },
      ]

  let chartType = 'bar'
  if (categoryColumn === 'mes' && seriesColumn) {
    chartType = 'grouped_bar'
  } else if (categoryColumn === 'mes') {
    chartType = labels.length <= 6 ? 'bar' : 'line'
  } else if (seriesColumn) {
    chartType = 'grouped_bar'
  } else if (labels.length >= 7 || Math.max(...labels.map((label) => label.length), 0) >= 12) {
    chartType = 'horizontal_bar'
  }

  return {
    chart_type: chartType,
    category_column: categoryColumn,
    value_column: valueColumn,
    series_column: seriesColumn,
    labels,
    series,
    value_format: valueColumn.toLowerCase().includes('valor') ? 'currency' : 'number',
  }
}

function disposeChart() {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

function formatHistoryDate(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

async function loadHistory() {
  isLoadingHistory.value = true

  try {
    const response = await getScriptHistory({ limit: 30 })
    historyItems.value = response.items || []
  } catch {
    historyItems.value = []
  } finally {
    isLoadingHistory.value = false
  }
}

function selectHistoryItem(item) {
  selectedHistoryId.value = item.id
  prompt.value = item.question
}

function toggleHistory() {
  historyCollapsed.value = !historyCollapsed.value
}

function formatAxisMetric(value, isCurrencySeries) {
  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) {
    return value
  }

  if (isCurrencySeries) {
    if (Math.abs(numericValue) >= 1000) {
      return `R$ ${compactNumberFormatter.format(numericValue)}`
    }

    return currencyFormatter.format(numericValue)
  }

  return compactNumberFormatter.format(numericValue)
}

function formatMetricLabel(value, isCurrencySeries) {
  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) {
    return '-'
  }

  return isCurrencySeries
    ? currencyFormatter.format(numericValue)
    : numericValue.toLocaleString('pt-BR')
}

async function renderChart() {
  await nextTick()

  if (!chartElement.value || !chartConfig.value) {
    disposeChart()
    return
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartElement.value)
  }

  const isCurrencySeries = chartConfig.value.value_format === 'currency'
  const chartType = chartConfig.value.chart_type || 'bar'
  const seriesType = chartType === 'line' ? 'line' : 'bar'
  const isLine = chartType === 'line'
  const isHorizontalBar = chartType === 'horizontal_bar'
  const isGroupedSeries = Boolean(chartConfig.value.series_column)
  const isDarkTheme = theme.value === 'dark'
  const chartTextColor = isDarkTheme ? '#f6fbff' : '#10243a'
  const chartMutedColor = isDarkTheme ? '#c4d0dc' : '#4f647a'
  const chartGridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.12)' : 'rgba(35, 65, 95, 0.18)'
  const chartAxisColor = isDarkTheme ? 'rgba(255, 255, 255, 0.2)' : 'rgba(35, 65, 95, 0.22)'
  const chartTooltipBg = isDarkTheme ? 'rgba(11, 22, 33, 0.96)' : 'rgba(255, 255, 255, 0.98)'
  const chartTooltipBorder = isDarkTheme ? 'rgba(255, 255, 255, 0.16)' : 'rgba(35, 65, 95, 0.14)'
  const chartBackground = isDarkTheme ? 'transparent' : '#ffffff'
  const series = (chartConfig.value.series || []).map((item, index) => ({
    name: item.name,
    type: seriesType,
    smooth: isLine,
    connectNulls: false,
    barMaxWidth: isHorizontalBar ? 26 : 34,
    data: item.data,
    symbolSize: isLine ? 8 : 0,
    showSymbol: isLine,
    emphasis: {
      focus: isGroupedSeries ? 'series' : 'self',
    },
    lineStyle: {
      width: 3,
    },
    itemStyle: {
      borderRadius: isLine ? 6 : (isHorizontalBar ? [0, 4, 4, 0] : [4, 4, 0, 0]),
    },
    areaStyle: undefined,
    label: !isGroupedSeries && !isLine
      ? {
          show: true,
          position: isHorizontalBar ? 'right' : 'top',
          color: chartTextColor,
          fontWeight: 700,
          formatter(params) {
            return formatMetricLabel(params.value, isCurrencySeries)
          },
        }
      : undefined,
    z: index + 1,
  }))

  chartInstance.setOption({
    animationDuration: 500,
    backgroundColor: chartBackground,
    color: isDarkTheme
      ? ['#7c3aed', '#38bdf8', '#f59e0b', '#cbd5e1', '#14b8a6', '#f472b6']
      : ['#5cb3a1', '#3b82c4', '#f28b28', '#b8b8b8', '#2d6ea3', '#6aa6d8'],
    legend: {
      show: isGroupedSeries || !isLine,
      bottom: 0,
      left: 'center',
      itemWidth: 14,
      textStyle: {
        color: chartMutedColor,
        fontWeight: 500,
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: isLine ? 'line' : 'shadow' },
      backgroundColor: chartTooltipBg,
      borderColor: chartTooltipBorder,
      borderWidth: 1,
      textStyle: {
        color: chartTextColor,
      },
      formatter(params) {
        const lines = [`<strong>${params[0].axisValue}</strong>`]
        for (const item of params) {
          if (item.value === null || item.value === undefined) {
            continue
          }
          const value = formatMetricLabel(item.value, isCurrencySeries)
          lines.push(`${item.marker}${item.seriesName}: ${value}`)
        }
        return lines.join('<br/>')
      },
    },
    grid: {
      left: isHorizontalBar ? 110 : 36,
      right: 24,
      top: 26,
      bottom: !isLine || isGroupedSeries ? 68 : 44,
      containLabel: true,
    },
    xAxis: isHorizontalBar
      ? {
          type: 'value',
          splitNumber: 5,
          splitLine: {
            lineStyle: {
              color: chartGridColor,
            },
          },
          axisLine: {
            show: false,
          },
          axisTick: {
            show: false,
          },
          axisLabel: {
            color: chartMutedColor,
            formatter(value) {
              return formatAxisMetric(value, isCurrencySeries)
            },
          },
        }
      : {
          type: 'category',
          data: chartConfig.value.labels,
          boundaryGap: true,
          axisTick: {
            show: false,
          },
          axisLine: {
            lineStyle: {
              color: chartAxisColor,
            },
          },
          axisLabel: {
            interval: 0,
            rotate: chartConfig.value.labels.length > 6 ? 16 : 0,
            color: chartMutedColor,
            fontWeight: 500,
            margin: 14,
          },
        },
    yAxis: isHorizontalBar
      ? {
          type: 'category',
          data: chartConfig.value.labels,
          axisTick: {
            show: false,
          },
          axisLine: {
            show: false,
          },
          axisLabel: {
            color: chartMutedColor,
            fontWeight: 600,
          },
        }
      : {
          type: 'value',
          splitNumber: 6,
          splitLine: {
            lineStyle: {
              color: chartGridColor,
            },
          },
          axisLine: {
            show: false,
          },
          axisTick: {
            show: false,
          },
          axisLabel: {
            color: chartMutedColor,
            fontWeight: 500,
            formatter(value) {
              return formatAxisMetric(value, isCurrencySeries)
            },
          },
        },
    series,
  }, true)
  chartInstance.resize()
}

async function validateSession() {
  try {
    const response = await getAuthenticatedUser()
    currentUser.value = response.user
    await loadHistory()
  } catch {
    clearAuthSession()
    router.push({ name: 'login' })
  } finally {
    isCheckingAuth.value = false
  }
}

async function handleSubmit() {
  errorMessage.value = ''
  result.value = null
  isLoading.value = true

  try {
    result.value = await generateScript(prompt.value, {
      execute: true,
      previewLimit: 20,
    })
    selectedMonths.value = monthOptions.value.map((item) => item.value)
    await loadHistory()
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

function toggleMonth(monthValue) {
  if (selectedMonths.value.includes(monthValue)) {
    selectedMonths.value = selectedMonths.value.filter((value) => value !== monthValue)
    return
  }

  selectedMonths.value = [...selectedMonths.value, monthValue].sort((left, right) => left.localeCompare(right))
}

function selectAllMonths() {
  selectedMonths.value = monthOptions.value.map((item) => item.value)
}

function logout() {
  clearAuthSession()
  router.push({ name: 'login' })
}

function handleThemeChange(event) {
  theme.value = event.detail?.theme || document.documentElement.dataset.theme || 'light'
  renderChart()
}

onMounted(() => {
  window.addEventListener('themechange', handleThemeChange)
  validateSession()
})

watch(
  () => result.value?.preview_rows,
  (rows) => {
    if (!rows?.length || !previewColumns.value.includes('mes')) {
      selectedMonths.value = []
      return
    }

    selectedMonths.value = [...new Set(rows.map((row) => String(row.mes)))].sort((left, right) => left.localeCompare(right))
  },
  { immediate: true }
)

watch(chartConfig, () => {
  renderChart()
})

onBeforeUnmount(() => {
  window.removeEventListener('themechange', handleThemeChange)
  disposeChart()
})
</script>

<template>
  <main class="prompt-layout" :class="{ 'prompt-layout--history-collapsed': historyCollapsed }">
    <aside class="history-sidebar" :class="{ 'history-sidebar--collapsed': historyCollapsed }">
      <div class="history-panel">
        <div class="history-header">
          <div>
            <span class="eyebrow">Histórico</span>
            <h2>Consultas recentes</h2>
            <p v-if="!historyCollapsed && canViewAllHistory">Visível para todos os usuários cadastrados.</p>
            <p v-else-if="!historyCollapsed">Mostrando apenas as suas consultas.</p>
          </div>

          <button
            type="button"
            class="history-toggle"
            :aria-expanded="(!historyCollapsed).toString()"
            :aria-label="historyCollapsed ? 'Expandir histórico' : 'Recolher histórico'"
            @click="toggleHistory"
          >
            <span class="history-toggle__icon" :class="{ 'history-toggle__icon--collapsed': historyCollapsed }">
              ‹
            </span>
          </button>
        </div>

        <div v-if="!historyCollapsed && (isCheckingAuth || isLoadingHistory)" class="history-state">
          Carregando histórico...
        </div>

        <div v-else-if="!historyCollapsed && !historyItems.length" class="history-state">
          Nenhuma consulta registrada ainda.
        </div>

        <div v-else-if="!historyCollapsed" class="history-list">
          <button
            v-for="item in historyItems"
            :key="item.id"
            type="button"
            class="history-item"
            :class="{ 'history-item--active': selectedHistoryId === item.id }"
            @click="selectHistoryItem(item)"
          >
            <strong>{{ item.question }}</strong>
            <span v-if="canViewAllHistory" class="history-meta">{{ item.requested_by }}</span>
            <span class="history-meta">{{ formatHistoryDate(item.created_at) }}</span>
          </button>
        </div>
      </div>
    </aside>

    <section class="prompt-shell">
      <header class="topbar">
        <div>
          <span class="eyebrow">Assistente autenticado</span>
          <h1>Escreva o prompt para gerar um SQL inicial.</h1>
          <p>
            Logado como <strong>{{ welcomeLabel }}</strong>
            <template v-if="currentRole"> - <strong>{{ currentRole }}</strong></template>.
          </p>
        </div>

        <button type="button" class="secondary-button" @click="logout">Sair</button>
      </header>

      <section v-if="isCheckingAuth" class="status-card">
        <p>Validando autenticação...</p>
      </section>

      <template v-else>
        <section class="input-card">
          <label for="prompt">Prompt de comando</label>
          <textarea
            id="prompt"
            v-model.trim="prompt"
            rows="8"
            placeholder="Ex.: Quero o volume de produção por planta nos últimos 3 meses para montar um gráfico no Power BI."
          />

          <div class="actions">
            <button type="button" :disabled="!prompt || isLoading" @click="handleSubmit">
              {{ isLoading ? 'Gerando SQL...' : 'Gerar SQL' }}
            </button>
          </div>

          <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        </section>

        <section v-if="result?.user_message" class="status-card status-card--message">
          <p>{{ result.user_message }}</p>
        </section>

        <section v-if="result" class="result-grid">
          <article v-if="isAdmin && hasUsableInterpretation" class="result-card">
            <h2>Interpretação da pergunta</h2>
            <ul>
              <li><strong>Domínio:</strong> {{ result.interpretation.domain }}</li>
              <li><strong>Métrica:</strong> {{ result.interpretation.metric }}</li>
              <li><strong>Dimensões:</strong> {{ result.interpretation.dimensions.join(', ') }}</li>
              <li><strong>Período:</strong> {{ result.interpretation.period_label }}</li>
              <li><strong>Visual sugerido:</strong> {{ result.interpretation.chart_suggestion }}</li>
            </ul>
          </article>

          <article v-if="isAdmin && hasUsableInterpretation" class="result-card">
            <h2>Tabelas sugeridas</h2>
            <ul>
              <li v-for="item in result.suggested_tables" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article v-if="isAdmin && hasUsableInterpretation" class="result-card">
            <h2>Filtros sugeridos</h2>
            <ul>
              <li v-for="item in result.suggested_filters" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article v-if="isAdmin && hasUsableInterpretation" class="result-card result-card--wide">
            <h2>Campos relevantes</h2>
            <div class="field-grid">
              <div v-for="item in result.relevant_fields" :key="`${item.table}-${item.field}`" class="field-chip">
                <strong>{{ item.table }}.{{ item.field }}</strong>
                <span>{{ item.label }}</span>
                <small>{{ item.description }}</small>
              </div>
            </div>
          </article>

          <article v-if="isAdmin && hasUsableInterpretation" class="result-card result-card--wide">
            <h2>Joins sugeridos</h2>
            <ul>
              <li v-for="item in result.join_suggestions" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article class="result-card result-card--wide">
            <h2>Resultado da busca</h2>
            <p v-if="result.preview_row_count" class="result-caption">
              {{ filteredPreviewRows.length }} linha(s) visível(is) de {{ result.preview_row_count }} retornada(s) para validação rápida.
            </p>
            <div v-if="monthOptions.length" class="month-filter">
              <div class="month-filter__header">
                <strong>Filtrar meses</strong>
                <button type="button" class="month-filter__action" @click="selectAllMonths">
                  Selecionar todos
                </button>
              </div>
              <div class="month-filter__chips">
                <button
                  v-for="option in monthOptions"
                  :key="option.value"
                  type="button"
                  class="month-chip"
                  :class="{ 'month-chip--active': selectedMonths.includes(option.value) }"
                  @click="toggleMonth(option.value)"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>
            <div v-if="filteredPreviewRows.length" class="table-wrapper">
              <table class="preview-table">
                <thead>
                  <tr>
                    <th v-for="column in previewColumns" :key="column">{{ column }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in filteredPreviewRows" :key="index">
                    <td v-for="column in previewColumns" :key="column">
                      {{ formatPreviewValue(column, row[column]) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="result-caption">
              {{ monthOptions.length ? 'Nenhum mês está selecionado no filtro atual.' : (result.user_message || 'Nenhuma linha foi retornada para este preview.') }}
            </p>
          </article>

          <article v-if="chartConfig && filteredPreviewRows.length" class="result-card result-card--wide">
            <h2>Visualização gráfica</h2>
            <p class="result-caption">
              Tipo escolhido automaticamente: <strong>{{ chartTypeLabel }}</strong>.
            </p>
            <p class="result-caption">
              Gráfico montado a partir das colunas <strong>{{ chartConfig.category_column }}</strong> e
              <strong>{{ chartConfig.value_column }}</strong>
              <template v-if="chartConfig.series_column">
                , segmentado por <strong>{{ chartConfig.series_column }}</strong>
              </template>.
            </p>
            <div ref="chartElement" class="chart-surface"></div>
          </article>

          <article v-if="isAdmin && result.draft_script" class="result-card result-card--wide result-card--sql">
            <h2>SQL gerado</h2>
            <pre>{{ result.draft_script }}</pre>
          </article>
        </section>
      </template>
    </section>
  </main>
</template>

<style scoped>
.prompt-layout {
  min-height: 100vh;
  padding: 1.25rem;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 1.25rem;
  transition: grid-template-columns 260ms ease, gap 260ms ease;
}

.prompt-layout--history-collapsed {
  grid-template-columns: 78px minmax(0, 1fr);
}

.prompt-shell {
  display: grid;
  gap: 1.25rem;
}

.history-sidebar {
  min-width: 0;
  transition: width 260ms ease, transform 260ms ease, opacity 220ms ease;
}

.history-sidebar--collapsed {
  width: 78px;
}

.history-panel,
.topbar,
.input-card,
.result-card,
.status-card {
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 24px;
  box-shadow: var(--panel-shadow);
  transition:
    background 220ms ease,
    border-color 220ms ease,
    box-shadow 220ms ease;
}

.history-panel {
  position: sticky;
  top: 1.25rem;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  max-height: calc(100vh - 2.5rem);
  overflow: hidden;
  transition: padding 260ms ease, border-radius 260ms ease;
}

.history-header {
  padding: 1.25rem 1.25rem 0;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  min-height: 46px;
}

.history-header h2 {
  margin: 0.35rem 0 0;
}

.history-header p {
  margin: 0.65rem 0 0;
  color: #4f647a;
  font-size: 0.92rem;
}

.history-list {
  display: grid;
  gap: 0.75rem;
  padding: 1rem 1rem 1.25rem;
  overflow-y: auto;
  opacity: 1;
  transition: opacity 220ms ease;
}

.history-item {
  display: grid;
  gap: 0.35rem;
  text-align: left;
  background: #0f2742;
  color: #f8fbff;
  border: 1px solid transparent;
  border-radius: 18px;
  padding: 0.95rem 1rem;
}

.history-item strong {
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.35;
}

.history-item--active {
  border-color: rgba(244, 162, 97, 0.9);
  box-shadow: 0 0 0 3px rgba(244, 162, 97, 0.18);
}

.history-meta {
  color: rgba(248, 251, 255, 0.74);
  font-size: 0.82rem;
}

.history-state {
  padding: 1.1rem 1.25rem 1.4rem;
  color: #4f647a;
}

.history-toggle {
  width: 64px;
  min-width: 64px;
  height: 46px;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  background: #edf3f9;
  color: #0f2742;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.history-toggle__icon {
  font-size: 1.35rem;
  line-height: 1;
  transition: transform 260ms ease;
}

.history-toggle__icon--collapsed {
  transform: rotate(180deg);
}

.history-sidebar--collapsed .history-header {
  padding: 0;
  min-height: 46px;
  align-items: flex-start;
}

.history-sidebar--collapsed .history-header > div {
  display: none;
}

.history-sidebar--collapsed .history-panel {
  grid-template-rows: auto;
  background: transparent;
  border: 0;
  box-shadow: none;
  max-height: none;
}

.history-sidebar--collapsed .history-toggle {
  width: 58px;
  min-width: 58px;
  height: 46px;
  padding: 0.85rem 0;
}

.topbar {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  padding: 1.5rem;
}

.eyebrow {
  display: inline-block;
  color: var(--accent-primary);
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.topbar h1,
.result-card h2 {
  margin: 0.35rem 0 0;
}

.topbar p {
  margin: 0.75rem 0 0;
  color: var(--text-secondary);
}

.input-card,
.status-card,
.result-card {
  padding: 1.5rem;
}

.input-card {
  display: grid;
  gap: 0.9rem;
}

.input-card label {
  font-weight: 700;
}

.input-card textarea {
  width: 100%;
  resize: vertical;
  padding: 1rem;
  border: 1px solid var(--input-border);
  border-radius: 18px;
  background: var(--input-bg);
  color: var(--text-primary);
}

.actions,
.topbar {
  display: flex;
}

button {
  border: 1px solid transparent;
  border-radius: 14px;
  padding: 0.85rem 1.1rem;
  font-weight: 800;
  cursor: pointer;
  backdrop-filter: blur(16px) saturate(1.18);
}

.actions button {
  background:
    var(--button-surface) padding-box,
    var(--button-border) border-box;
  color: var(--button-text);
  box-shadow: var(--button-shadow);
}

.secondary-button {
  background:
    var(--secondary-button-surface) padding-box,
    var(--button-border) border-box;
  color: var(--secondary-button-text);
  box-shadow: var(--button-shadow);
}

button:disabled {
  opacity: 0.72;
  cursor: progress;
}

.error-message {
  margin: 0;
  color: #b42318;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}

.result-card ul {
  margin: 1rem 0 0;
  padding-left: 1.1rem;
  color: var(--text-secondary);
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.9rem;
  margin-top: 1rem;
}

.field-chip {
  display: grid;
  gap: 0.25rem;
  padding: 0.9rem;
  border-radius: 16px;
  background: var(--surface-bg);
  border: 1px solid var(--panel-border);
}

.field-chip span,
.field-chip small {
  color: var(--text-secondary);
}

.result-card pre {
  margin: 1rem 0 0;
  padding: 1rem;
  overflow: auto;
  border-radius: 18px;
  background: #0f2742;
  color: #f8fbff;
}

.result-caption {
  margin: 1rem 0 0;
  color: var(--text-secondary);
}

.month-filter {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid rgba(16, 36, 58, 0.08);
  border-radius: 18px;
  background: #f8fbff;
}

.month-filter__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.month-filter__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.9rem;
}

.month-filter__action,
.month-chip {
  background: #edf3f9;
  color: #0f2742;
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  font-weight: 700;
}

.month-chip--active {
  background: #0f2742;
  color: #ffffff;
}

.table-wrapper {
  margin-top: 1rem;
  overflow-x: auto;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  border-radius: 18px;
  overflow: hidden;
  background: var(--surface-bg);
}

.preview-table th,
.preview-table td {
  padding: 0.9rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--panel-border);
}

.preview-table th {
  background: var(--surface-strong);
  color: var(--text-primary);
  font-size: 0.9rem;
}

.preview-table td {
  color: var(--text-primary);
}

.chart-surface {
  margin-top: 1rem;
  width: 100%;
  min-height: 360px;
  border-radius: 18px;
  padding: 0.5rem;
  border: 1px solid var(--panel-border);
  background: linear-gradient(180deg, var(--surface-bg) 0%, var(--surface-strong) 100%);
}

.result-card--sql pre {
  background: var(--sql-bg);
  color: var(--sql-text);
}

.result-card--wide {
  grid-column: 1 / -1;
}

@media (max-width: 760px) {
  .prompt-layout {
    grid-template-columns: 1fr;
  }

  .prompt-layout--history-collapsed {
    grid-template-columns: 1fr;
  }

  .history-panel {
    position: static;
    max-height: none;
  }

  .history-list {
    max-height: 260px;
  }

  .history-sidebar--collapsed {
    width: auto;
  }

  .topbar,
  .result-grid {
    flex-direction: column;
    grid-template-columns: 1fr;
  }
}
</style>
