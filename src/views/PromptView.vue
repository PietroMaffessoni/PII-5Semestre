<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

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
let echartsModule = null

const welcomeLabel = computed(() => currentUser.value?.usuario || 'usuário autenticado')
const currentRole = computed(() => currentUser.value?.role || '')
const isAdmin = computed(() => currentRole.value === 'admin')
const isManager = computed(() => currentRole.value === 'gerente')
const canViewSharedHistory = computed(() => isAdmin.value || isManager.value)
const historyScopeLabel = computed(() => {
  if (isAdmin.value) {
    return 'Visível para todos os usuários cadastrados.'
  }

  if (isManager.value) {
    return 'Visível para gerentes e funcionários.'
  }

  return 'Mostrando apenas as suas consultas.'
})
const hasUsableInterpretation = computed(() => Boolean(result.value?.is_understood))
const hasAdminDetails = computed(() => (
  isAdmin.value
  && hasUsableInterpretation.value
  && Boolean(result.value?.interpretation)
))
const isDarkTheme = computed(() => theme.value === 'dark')
const previewColumns = computed(() => {
  if (!result.value?.preview_rows?.length) {
    return []
  }

  return Object.keys(result.value.preview_rows[0])
})
const monthOptions = computed(() => {
  if (result.value?.preview_rows?.length && previewColumns.value.includes('mes')) {
    const uniqueValues = [...new Set(result.value.preview_rows.map((row) => String(row.mes)))]
      .sort(compareMonthValues)

    return uniqueValues.map((value) => ({
      value,
      label: formatPreviewValue('mes', value),
    }))
  }

  const payload = result.value?.chart_payload
  if (payload?.category_column !== 'mes' || !payload.labels?.length) {
    return []
  }

  return payload.labels.map((label) => ({
    value: String(label),
    label: String(label),
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
  return rows
    .filter((row) => allowed.has(String(row.mes)))
    .sort(comparePreviewRows)
})
const visibleMonthRangeLabel = computed(() => {
  if (!filteredPreviewRows.value.length || !previewColumns.value.includes('mes')) {
    if (!selectedMonths.value.length || result.value?.chart_payload?.category_column !== 'mes') {
      return ''
    }

    const selectedLabels = monthOptions.value
      .filter((option) => selectedMonths.value.includes(option.value))
      .map((option) => option.label)

    if (!selectedLabels.length) {
      return ''
    }

    if (selectedLabels.length === 1) {
      return selectedLabels[0]
    }

    return `${selectedLabels[0]} a ${selectedLabels[selectedLabels.length - 1]}`
  }

  if (!previewColumns.value.includes('mes')) {
    return ''
  }

  const months = [...new Set(filteredPreviewRows.value.map((row) => String(row.mes)))]
    .sort(compareMonthValues)

  if (months.length === 1) {
    return formatPreviewValue('mes', months[0])
  }

  return `${formatPreviewValue('mes', months[0])} a ${formatPreviewValue('mes', months[months.length - 1])}`
})
const periodExclusionNotice = computed(() => {
  const question = result.value?.question || ''
  const normalizedQuestion = normalizeSearchText(question)
  const match = normalizedQuestion.match(/\bultim[oa]s?\s+(\d+)\s+mes(?:es)?\b/)

  if (!match || includesCurrentMonth(normalizedQuestion)) {
    return ''
  }

  const monthText = Number(match[1]) === 1 ? 'mes' : 'meses'
  return `"Últimos ${match[1]} ${monthText}" considera meses completos encerrados e não inclui o mês atual. Para incluir o mês atual, especifique isso no prompt.`
})
const chartConfig = computed(() => (
  buildLocalChartPayload(filteredPreviewRows.value)
  || filterChartPayloadBySelectedMonths(result.value?.chart_payload)
  || null
))
const hasVisiblePreviewRows = computed(() => filteredPreviewRows.value.length > 0)
const areAllMonthsSelected = computed(() => (
  monthOptions.value.length > 0
  && selectedMonths.value.length === monthOptions.value.length
  && monthOptions.value.every((option) => selectedMonths.value.includes(option.value))
))
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
const shortMonthLabels = {
  '01': 'Jan',
  '02': 'Fev',
  '03': 'Mar',
  '04': 'Abr',
  '05': 'Mai',
  '06': 'Jun',
  '07': 'Jul',
  '08': 'Ago',
  '09': 'Set',
  '10': 'Out',
  '11': 'Nov',
  '12': 'Dez',
}

function parseMonthParts(value) {
  const match = String(value).match(/^(\d{4})-(\d{2})-/)
  if (!match) {
    return null
  }

  return {
    year: match[1],
    month: match[2],
  }
}

function normalizeSearchText(value) {
  return String(value)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
}

function includesCurrentMonth(normalizedQuestion) {
  return [
    'incluindo o mes atual',
    'incluindo mes atual',
    'inclui o mes atual',
    'incluir o mes atual',
    'com o mes atual',
    'contando com o mes atual',
    'considerando o mes atual',
  ].some((pattern) => normalizedQuestion.includes(pattern))
}

function compareMonthValues(left, right) {
  const leftParts = parseMonthParts(left)
  const rightParts = parseMonthParts(right)

  if (leftParts && rightParts) {
    return `${leftParts.year}-${leftParts.month}`.localeCompare(`${rightParts.year}-${rightParts.month}`)
  }

  return String(left).localeCompare(String(right))
}

function comparePreviewRows(left, right) {
  const monthComparison = compareMonthValues(left.mes, right.mes)
  if (monthComparison !== 0) {
    return monthComparison
  }

  return previewColumns.value
    .filter((column) => column !== 'mes')
    .reduce((comparison, column) => {
      if (comparison !== 0) {
        return comparison
      }

      return String(left[column] ?? '').localeCompare(String(right[column] ?? ''), 'pt-BR')
    }, 0)
}

function formatMonthLabel(value, style = 'long') {
  const parts = parseMonthParts(value)
  if (!parts) {
    return value
  }

  if (style === 'short') {
    return `${shortMonthLabels[parts.month] || parts.month}/${parts.year}`
  }

  return `${monthLabels[parts.month] || parts.month} de ${parts.year}`
}

function formatPreviewValue(column, value) {
  if (value === null || value === undefined) {
    return ''
  }

  if (column === 'mes') {
    return formatMonthLabel(value)
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
      return formatMonthLabel(value, 'short')
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
    value_format: isCurrencyMetric(valueColumn) ? 'currency' : 'number',
  }
}

function isCurrencyMetric(column) {
  const normalized = String(column).toLowerCase()
  return ['valor', 'salario', 'rendimento', 'beneficio', 'desconto', 'encargo', 'custo']
    .some((term) => normalized.includes(term))
}

function filterChartPayloadBySelectedMonths(payload) {
  if (!payload) {
    return null
  }

  if (payload.category_column !== 'mes') {
    return payload
  }

  if (!selectedMonths.value.length) {
    return null
  }

  const selected = new Set(selectedMonths.value)
  const selectedIndexes = (payload.labels || [])
    .map((label, index) => ({ label: String(label), index }))
    .filter((item) => selected.has(item.label))

  if (!selectedIndexes.length) {
    return null
  }

  return {
    ...payload,
    labels: selectedIndexes.map((item) => item.label),
    series: (payload.series || []).map((serie) => ({
      ...serie,
      data: selectedIndexes.map((item) => serie.data?.[item.index] ?? null),
    })),
  }
}

function disposeChart() {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

async function loadEcharts() {
  if (echartsModule) {
    return echartsModule
  }

  const module = await import('../services/echarts')
  echartsModule = module.getEcharts()
  return echartsModule
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

function getHistoryStatusMessage(item, previewRows) {
  if (previewRows.length || item.chart_payload) {
    return ''
  }

  if (item.execution_status === 'not_understood') {
    return 'Essa pergunta foi salva no histórico, mas não foi compreendida para gerar uma consulta.'
  }

  if (item.execution_status === 'no_data') {
    return 'Essa consulta foi salva no histórico, mas não retornou dados para os filtros informados.'
  }

  if (item.execution_status === 'blocked') {
    return 'Essa consulta foi bloqueada na validação de segurança e não possui dados salvos.'
  }

  return 'Essa consulta não possui dados salvos no histórico.'
}

function buildResultFromHistoryItem(item) {
  const previewRows = Array.isArray(item.result_preview) ? item.result_preview : []
  const isUnderstood = item.execution_status !== 'not_understood'
  const previewRowCount = Number.isFinite(Number(item.row_count))
    ? Number(item.row_count)
    : previewRows.length

  return {
    question: item.question,
    context: null,
    status: item.execution_status || 'history',
    is_understood: isUnderstood,
    user_message: getHistoryStatusMessage(item, previewRows),
    requested_by: item.requested_by,
    preview_rows: previewRows,
    preview_row_count: previewRowCount,
    chart_payload: item.chart_payload || buildLocalChartPayload(previewRows),
    draft_script: item.generated_sql || '',
    retrieval_mode: item.retrieval_mode || 'history',
    interpretation: null,
    suggested_tables: [],
    suggested_filters: [],
    relevant_fields: [],
    join_suggestions: [],
  }
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
  errorMessage.value = ''
  result.value = buildResultFromHistoryItem(item)
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

  const echarts = await loadEcharts()

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
  const labelCount = chartConfig.value.labels?.length || 0
  const seriesCount = chartConfig.value.series?.length || 0
  const chartWidth = chartElement.value.clientWidth || window.innerWidth
  const isCompactChart = chartWidth < 560
  const hasDenseCategories = labelCount > (isCompactChart ? 4 : 7)
  const shouldUseDataZoom = !isHorizontalBar && labelCount > (isCompactChart ? 5 : 9)
  const shouldShowValueLabels = !isGroupedSeries && !isLine && !isCompactChart && labelCount <= 6
  const axisLabelRotation = hasDenseCategories ? (isCompactChart ? 42 : 24) : 0
  const axisLabelInterval = hasDenseCategories ? 'auto' : 0
  const formatCategoryAxisLabel = (value) => {
    const text = String(value)
    const maxLength = isCompactChart ? 9 : 14
    return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text
  }
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
    label: shouldShowValueLabels
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
      type: seriesCount > 3 || isCompactChart ? 'scroll' : 'plain',
      bottom: 0,
      left: 'center',
      itemWidth: 14,
      itemGap: isCompactChart ? 8 : 12,
      pageIconColor: chartMutedColor,
      pageTextStyle: {
        color: chartMutedColor,
      },
      textStyle: {
        color: chartMutedColor,
        fontWeight: 500,
        overflow: 'truncate',
        width: isCompactChart ? 96 : 160,
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: isLine ? 'line' : 'shadow' },
      confine: true,
      backgroundColor: chartTooltipBg,
      borderColor: chartTooltipBorder,
      borderWidth: 1,
      extraCssText: [
        `max-width: ${isCompactChart ? 260 : 360}px`,
        'white-space: normal',
        'overflow-wrap: anywhere',
        'box-sizing: border-box',
      ].join(';'),
      textStyle: {
        color: chartTextColor,
      },
      position(point, _params, _dom, _rect, size) {
        const gap = 8
        const tooltipWidth = size.contentSize[0]
        const tooltipHeight = size.contentSize[1]
        const viewWidth = size.viewSize[0]
        const viewHeight = size.viewSize[1]
        const x = Math.min(Math.max(point[0] + gap, gap), Math.max(gap, viewWidth - tooltipWidth - gap))
        const preferredY = point[1] - tooltipHeight - gap
        const fallbackY = point[1] + gap
        const y = preferredY >= gap
          ? preferredY
          : Math.min(Math.max(fallbackY, gap), Math.max(gap, viewHeight - tooltipHeight - gap))

        return [x, y]
      },
      formatter(params) {
        const lines = [`<strong class="chart-tooltip-title">${params[0].axisValue}</strong>`]
        for (const item of params) {
          if (item.value === null || item.value === undefined) {
            continue
          }
          const value = formatMetricLabel(item.value, isCurrencySeries)
          lines.push(`<span class="chart-tooltip-row">${item.marker}<span>${item.seriesName}: ${value}</span></span>`)
        }
        return lines.join('<br/>')
      },
    },
    grid: {
      left: isHorizontalBar ? (isCompactChart ? 88 : 120) : (isCompactChart ? 20 : 36),
      right: isHorizontalBar ? (isCompactChart ? 30 : 42) : (isCompactChart ? 16 : 24),
      top: 28,
      bottom: shouldUseDataZoom ? 98 : (!isLine || isGroupedSeries ? 74 : 48),
      containLabel: true,
    },
    dataZoom: shouldUseDataZoom
      ? [
          {
            type: 'inside',
            start: 0,
            end: Math.min(100, Math.max(38, Math.round((5 / labelCount) * 100))),
          },
          {
            type: 'slider',
            height: 18,
            bottom: 42,
            start: 0,
            end: Math.min(100, Math.max(38, Math.round((5 / labelCount) * 100))),
            brushSelect: false,
            borderColor: chartAxisColor,
            fillerColor: isDarkTheme ? 'rgba(124, 58, 237, 0.26)' : 'rgba(15, 118, 110, 0.18)',
            handleSize: 14,
            textStyle: {
              color: chartMutedColor,
            },
          },
        ]
      : [],
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
            hideOverlap: true,
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
            interval: axisLabelInterval,
            rotate: axisLabelRotation,
            hideOverlap: true,
            color: chartMutedColor,
            fontWeight: 500,
            margin: isCompactChart ? 18 : 14,
            formatter: formatCategoryAxisLabel,
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
            hideOverlap: true,
            formatter: formatCategoryAxisLabel,
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

function clearMonthSelection() {
  selectedMonths.value = []
}

function toggleAllMonths() {
  if (areAllMonthsSelected.value) {
    clearMonthSelection()
    return
  }

  selectAllMonths()
}

function logout() {
  clearAuthSession()
  router.push({ name: 'login' })
}

function applyTheme(nextTheme) {
  theme.value = nextTheme
  document.documentElement.dataset.theme = nextTheme
  window.localStorage.setItem('theme', nextTheme)
  window.dispatchEvent(new CustomEvent('themechange', { detail: { theme: nextTheme } }))
}

function toggleTheme() {
  applyTheme(isDarkTheme.value ? 'light' : 'dark')
}

function handleThemeChange(event) {
  theme.value = event.detail?.theme || document.documentElement.dataset.theme || 'light'
  renderChart()
}

function handleWindowResize() {
  chartInstance?.resize()
  renderChart()
}

onMounted(() => {
  window.addEventListener('themechange', handleThemeChange)
  window.addEventListener('resize', handleWindowResize)
  validateSession()
})

watch(
  () => [result.value?.preview_rows, result.value?.chart_payload],
  () => {
    if (!monthOptions.value.length) {
      selectedMonths.value = []
      return
    }

    selectedMonths.value = monthOptions.value.map((item) => item.value)
  },
  { immediate: true }
)

watch(chartConfig, () => {
  renderChart()
})

onBeforeUnmount(() => {
  window.removeEventListener('themechange', handleThemeChange)
  window.removeEventListener('resize', handleWindowResize)
  disposeChart()
})
</script>

<template>
  <main
    class="prompt-layout"
    :class="{
      'prompt-layout--history-collapsed': historyCollapsed,
      'prompt-layout--dark': isDarkTheme,
    }"
  >
    <aside class="history-sidebar" :class="{ 'history-sidebar--collapsed': historyCollapsed }">
      <div class="history-panel">
        <div class="history-header">
          <div>
            <span class="eyebrow">Histórico</span>
            <h2>Consultas recentes</h2>
            <p v-if="!historyCollapsed">{{ historyScopeLabel }}</p>
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
            <span v-if="canViewSharedHistory" class="history-meta">{{ item.requested_by }}</span>
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

        <div class="topbar-actions">
          <button type="button" class="theme-action" :aria-pressed="isDarkTheme" @click="toggleTheme">
            <span class="theme-action__icon" aria-hidden="true"></span>
            {{ isDarkTheme ? 'Claro' : 'Escuro' }}
          </button>
          <button type="button" class="secondary-button" @click="logout">Sair</button>
        </div>
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
          <article v-if="hasAdminDetails" class="result-card">
            <h2>Interpretação da pergunta</h2>
            <ul>
              <li><strong>Domínio:</strong> {{ result.interpretation.domain }}</li>
              <li><strong>Métrica:</strong> {{ result.interpretation.metric }}</li>
              <li><strong>Dimensões:</strong> {{ result.interpretation.dimensions.join(', ') }}</li>
              <li><strong>Período:</strong> {{ result.interpretation.period_label }}</li>
              <li><strong>Visual sugerido:</strong> {{ result.interpretation.chart_suggestion }}</li>
            </ul>
          </article>

          <article v-if="hasAdminDetails" class="result-card">
            <h2>Tabelas sugeridas</h2>
            <ul>
              <li v-for="item in result.suggested_tables" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article v-if="hasAdminDetails" class="result-card">
            <h2>Filtros sugeridos</h2>
            <ul>
              <li v-for="item in result.suggested_filters" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article v-if="hasAdminDetails" class="result-card result-card--wide">
            <h2>Campos relevantes</h2>
            <div class="field-grid">
              <div v-for="item in result.relevant_fields" :key="`${item.table}-${item.field}`" class="field-chip">
                <strong>{{ item.table }}.{{ item.field }}</strong>
                <span>{{ item.label }}</span>
                <small>{{ item.description }}</small>
              </div>
            </div>
          </article>

          <article v-if="hasAdminDetails" class="result-card result-card--wide">
            <h2>Joins sugeridos</h2>
            <ul>
              <li v-for="item in result.join_suggestions" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article class="result-card result-card--wide">
            <h2>Resultado da busca</h2>
            <p v-if="result.preview_row_count && filteredPreviewRows.length" class="result-caption">
              {{ filteredPreviewRows.length }} linha(s) visível(is) de {{ result.preview_row_count }} retornada(s) para validação rápida.
            </p>
            <p v-if="visibleMonthRangeLabel" class="result-caption">
              Período exibido: <strong>{{ visibleMonthRangeLabel }}</strong>.
            </p>
            <p v-if="periodExclusionNotice" class="result-caption result-caption--notice">
              {{ periodExclusionNotice }}
            </p>
            <div v-if="monthOptions.length" class="month-filter">
              <div class="month-filter__header">
                <strong>Filtrar meses</strong>
                <button type="button" class="month-filter__action" @click="toggleAllMonths">
                  {{ areAllMonthsSelected ? 'Desselecionar todos' : 'Selecionar todos' }}
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
            <div v-if="hasVisiblePreviewRows" class="table-wrapper">
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
            <p v-else-if="chartConfig" class="result-caption">
              Resultado disponível na visualização gráfica abaixo.
            </p>
            <p v-else class="result-caption">
              {{ monthOptions.length ? 'Nenhum mês está selecionado no filtro atual.' : (result.user_message || 'Nenhuma linha foi retornada para este preview.') }}
            </p>
          </article>

          <article v-if="chartConfig" class="result-card result-card--wide">
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

.prompt-layout--dark .history-item {
  background: #7c3aed;
  box-shadow: 0 10px 24px rgba(124, 58, 237, 0.18);
}

.prompt-layout--dark .history-item--active {
  border-color: rgba(207, 217, 255, 0.95);
  box-shadow:
    0 0 0 3px rgba(124, 58, 237, 0.28),
    0 12px 28px rgba(124, 58, 237, 0.24);
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

.topbar-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  flex: 0 0 auto;
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

.theme-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 2.9rem;
  background:
    var(--secondary-button-surface) padding-box,
    var(--button-border) border-box;
  color: var(--secondary-button-text);
  box-shadow: var(--button-shadow);
}

.theme-action__icon {
  flex: 0 0 0.9rem;
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 999px;
  background: currentColor;
  box-shadow: inset -0.28rem -0.16rem 0 rgba(255, 248, 224, 0.9);
}

:global(:root[data-theme='dark']) .theme-action__icon {
  box-shadow: 0 0 0 0.2rem rgba(255, 255, 255, 0.12);
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

.result-caption--notice {
  padding: 0.75rem 0.9rem;
  border: 1px solid var(--panel-border);
  border-radius: 14px;
  background: var(--surface-bg);
}

.month-filter {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--panel-border);
  border-radius: 18px;
  background: var(--surface-bg);
  color: var(--text-primary);
  transition:
    background 220ms ease,
    border-color 220ms ease,
    color 220ms ease;
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
  background: var(--secondary-button-fill);
  color: var(--secondary-button-text);
  border: 1px solid var(--panel-border);
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  font-weight: 700;
}

.month-chip--active {
  background: #0f2742;
  color: #ffffff;
  border-color: transparent;
}

.prompt-layout--dark .month-filter {
  background: rgba(14, 27, 38, 0.86);
  border-color: rgba(220, 235, 255, 0.16);
}

.prompt-layout--dark .month-filter__action,
.prompt-layout--dark .month-chip {
  background: rgba(255, 255, 255, 0.08);
  color: #f6fbff;
  border-color: rgba(220, 235, 255, 0.16);
}

.prompt-layout--dark .month-chip--active {
  background: #7c3aed;
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 0 0 1px rgba(124, 58, 237, 0.38);
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

@media (max-width: 480px) {
  .prompt-layout {
    min-height: 100svh;
    padding: 0.75rem;
    padding-top: 4.25rem;
  }

  .prompt-shell {
    width: 100%;
    gap: 0.8rem;
  }

  .topbar,
  .input-card,
  .result-card,
  .status-card {
    border-radius: 16px;
  }

  .topbar {
    align-items: stretch;
    gap: 0.85rem;
    padding: 1rem;
  }

  .topbar-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .topbar h1 {
    font-size: clamp(1.25rem, 6vw, 1.55rem);
    line-height: 1.18;
  }

  .topbar p {
    line-height: 1.45;
    font-size: 0.93rem;
  }

  .eyebrow {
    font-size: 0.72rem;
    letter-spacing: 0.04em;
  }

  .input-card,
  .status-card,
  .result-card {
    padding: 1rem;
  }

  .input-card textarea {
    min-height: 9.5rem;
    padding: 0.85rem;
    border-radius: 14px;
    font-size: 0.95rem;
  }

  .actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .actions button,
  .theme-action,
  .secondary-button {
    flex: 1 1 8rem;
    min-height: 2.8rem;
  }

  .result-card h2 {
    font-size: 1.12rem;
    line-height: 1.25;
  }

  .result-card ul {
    padding-left: 1rem;
  }

  .result-grid {
    gap: 0.8rem;
  }

  .field-grid {
    grid-template-columns: 1fr;
    gap: 0.65rem;
  }

  .field-chip {
    padding: 0.75rem;
    border-radius: 12px;
  }

  .result-card pre {
    padding: 0.85rem;
    border-radius: 12px;
    font-size: 0.85rem;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .table-wrapper {
    max-width: 100%;
    border-radius: 12px;
    -webkit-overflow-scrolling: touch;
  }

  .preview-table {
    min-width: 520px;
    border-radius: 12px;
  }

  .preview-table th,
  .preview-table td {
    padding: 0.7rem 0.75rem;
    font-size: 0.86rem;
  }

  .chart-surface {
    min-height: 260px;
    border-radius: 12px;
  }
}

@media (max-width: 360px) {
  .prompt-layout {
    padding: 0.55rem;
    padding-top: 3.9rem;
  }

  .topbar,
  .input-card,
  .status-card,
  .result-card {
    padding: 0.85rem;
  }

  .topbar h1 {
    font-size: 1.18rem;
  }

  .topbar p,
  .input-card label,
  .result-caption {
    font-size: 0.88rem;
  }

  button {
    padding: 0.72rem 0.8rem;
    font-size: 0.9rem;
  }

  .input-card textarea {
    font-size: 0.9rem;
  }

  .chart-surface {
    min-height: 230px;
  }
}

.prompt-layout {
  width: min(1560px, 100%);
  margin: 0 auto;
  padding: clamp(0.85rem, 1.45vw, 1.25rem);
  align-items: start;
  gap: clamp(0.85rem, 1.15vw, 1.15rem);
}

.prompt-shell {
  gap: 1rem;
  min-width: 0;
}

.history-panel,
.topbar,
.input-card,
.result-card,
.status-card {
  border-radius: 20px;
  backdrop-filter: blur(18px) saturate(1.05);
  box-shadow: 0 18px 44px rgba(16, 36, 58, 0.08);
}

.history-panel {
  top: 1rem;
}

.history-header {
  padding: 1.1rem 1.1rem 0;
}

.history-header h2 {
  font-size: 1.08rem;
  line-height: 1.2;
}

.history-header p,
.history-meta,
.result-caption {
  color: var(--text-secondary);
}

.history-toggle {
  width: 56px;
  min-width: 56px;
  height: 44px;
  border-radius: 14px;
  background: var(--surface-bg);
  color: var(--text-primary);
  border: 1px solid var(--panel-border);
  box-shadow: none;
}

.history-toggle__icon {
  font-size: 1.2rem;
}

.history-list {
  padding: 0.95rem 0.95rem 1.1rem;
  gap: 0.7rem;
}

.history-item {
  background: linear-gradient(180deg, var(--surface-bg) 0%, var(--surface-strong) 100%);
  color: var(--text-primary);
  border-color: var(--panel-border);
  box-shadow: none;
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.history-item:hover {
  transform: translateY(-1px);
  border-color: rgba(15, 118, 110, 0.28);
}

.history-item strong {
  color: var(--text-primary);
}

.history-meta {
  color: var(--text-secondary);
}

.history-item--active {
  border-color: rgba(15, 118, 110, 0.5);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.14);
}

.topbar {
  align-items: center;
  padding: 1.35rem 1.4rem;
  gap: 1rem;
}

.topbar > div {
  min-width: 0;
  max-width: 64rem;
}

.topbar h1 {
  font-size: clamp(1.5rem, 2vw, 2.05rem);
  line-height: 1.12;
  letter-spacing: -0.02em;
  text-wrap: balance;
}

.topbar p {
  max-width: 64ch;
}

.input-card,
.status-card,
.result-card {
  padding: 1.35rem;
}

.input-card label {
  color: var(--text-primary);
}

.input-card textarea {
  min-height: 11rem;
  padding: 0.95rem 1rem;
  border-radius: 16px;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    background 220ms ease;
}

button,
input,
textarea {
  transition:
    transform 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease,
    background 220ms ease,
    color 220ms ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
}

button:active:not(:disabled) {
  transform: translateY(0);
}

button:focus-visible,
input:focus-visible,
textarea:focus-visible {
  box-shadow: var(--focus-ring);
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.actions button {
  min-width: 11rem;
}

.secondary-button {
  border: 1px solid var(--panel-border);
  box-shadow: none;
}

.result-grid {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.result-card h2 {
  font-size: 1.1rem;
  line-height: 1.2;
}

.result-card ul {
  margin: 0.9rem 0 0;
  padding-left: 1rem;
  display: grid;
  gap: 0.55rem;
}

.result-card li {
  line-height: 1.45;
}

.field-grid {
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 0.75rem;
}

.field-chip {
  padding: 0.85rem;
  border-radius: 14px;
  background: var(--surface-bg);
  border-color: var(--panel-border);
}

.field-chip strong {
  color: var(--text-primary);
}

.month-filter {
  margin-top: 0.9rem;
  padding: 0.95rem;
  border-radius: 16px;
  background: var(--surface-bg);
  border-color: var(--panel-border);
}

.month-filter__header {
  flex-wrap: wrap;
}

.month-filter__action,
.month-chip {
  background: var(--surface-strong);
  color: var(--text-primary);
  border-radius: 999px;
}

.month-chip--active {
  background: var(--accent-primary);
  color: #ffffff;
}

.table-wrapper {
  border: 1px solid var(--panel-border);
  border-radius: 16px;
  background: var(--surface-bg);
}

.preview-table {
  min-width: 100%;
}

.preview-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface-strong);
}

.preview-table td {
  background: transparent;
}

.chart-surface {
  min-height: 320px;
  border-radius: 16px;
  background: linear-gradient(180deg, var(--surface-bg) 0%, var(--surface-strong) 100%);
}

:global(.chart-tooltip-title) {
  display: block;
  max-width: 100%;
  overflow-wrap: anywhere;
  white-space: normal;
}

:global(.chart-tooltip-row) {
  display: inline-flex;
  max-width: 100%;
  gap: 0.25rem;
  align-items: flex-start;
  overflow-wrap: anywhere;
  white-space: normal;
}

:global(.chart-tooltip-row > span:last-child) {
  min-width: 0;
}

.result-card--sql pre {
  background: var(--sql-bg);
  color: var(--sql-text);
}

@media (max-width: 760px) {
  .prompt-layout {
    grid-template-columns: 1fr;
    padding-top: 4.1rem;
  }

  .history-panel {
    position: static;
    max-height: none;
  }

  .history-list {
    max-height: 260px;
  }

  .topbar,
  .input-card,
  .status-card,
  .result-card {
    padding: 1rem;
    border-radius: 16px;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }

  .actions button,
  .secondary-button {
    width: 100%;
  }

  .chart-surface {
    min-height: 340px;
  }
}

@media (max-width: 480px) {
  .prompt-layout {
    padding: 0.75rem;
    padding-top: 3.95rem;
  }

  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .topbar h1 {
    font-size: 1.35rem;
  }

  .history-header {
    padding: 0.95rem 0.95rem 0;
  }

  .history-list {
    padding: 0.85rem;
  }

  .history-item {
    padding: 0.85rem 0.9rem;
  }

  .input-card textarea {
    min-height: 9.75rem;
  }

  .chart-surface {
    min-height: 360px;
    padding: 0.35rem;
  }

  .preview-table th,
  .preview-table td {
    padding: 0.72rem 0.75rem;
    font-size: 0.86rem;
  }
}
</style>
