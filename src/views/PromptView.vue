<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

import { generateScript, getAuthenticatedUser } from '../services/api'
import { clearAuthSession, getCurrentUser } from '../services/auth'

const router = useRouter()
const prompt = ref('')
const result = ref(null)
const errorMessage = ref('')
const isLoading = ref(false)
const isCheckingAuth = ref(true)
const currentUser = ref(getCurrentUser())
const chartElement = ref(null)
let chartInstance = null

const welcomeLabel = computed(() => currentUser.value?.usuario || 'usuário autenticado')
const currentRole = computed(() => currentUser.value?.role || '')
const isAdmin = computed(() => currentRole.value === 'admin')
const hasUsableInterpretation = computed(() => Boolean(result.value?.is_understood))
const previewColumns = computed(() => {
  if (!result.value?.preview_rows?.length) {
    return []
  }

  return Object.keys(result.value.preview_rows[0])
})
const chartConfig = computed(() => result.value?.chart_payload || null)
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

function disposeChart() {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
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
  const series = (chartConfig.value.series || []).map((item, index) => ({
    name: item.name,
    type: seriesType,
    smooth: isLine,
    connectNulls: false,
    barMaxWidth: isHorizontalBar ? 28 : 44,
    data: item.data,
    symbolSize: isLine ? 10 : 0,
    showSymbol: isLine,
    emphasis: {
      focus: isGroupedSeries ? 'series' : 'self',
    },
    lineStyle: {
      width: 4,
    },
    itemStyle: {
      borderRadius: isLine ? 8 : (isHorizontalBar ? [0, 10, 10, 0] : [10, 10, 0, 0]),
    },
    areaStyle: !isGroupedSeries && isLine ? { opacity: 0.08 } : undefined,
    label: !isGroupedSeries && !isLine
      ? {
          show: true,
          position: isHorizontalBar ? 'right' : 'top',
          color: '#23415f',
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
    color: ['#1e5d8f', '#0f8b8d', '#f4a261', '#e76f51', '#6c8ebf', '#8ab17d'],
    legend: {
      show: isGroupedSeries,
      top: 0,
      left: 'center',
      itemWidth: 14,
      textStyle: {
        color: '#23415f',
        fontWeight: 600,
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: isLine ? 'line' : 'shadow' },
      backgroundColor: 'rgba(15, 39, 66, 0.95)',
      borderWidth: 0,
      textStyle: {
        color: '#f8fbff',
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
      left: isHorizontalBar ? 110 : 28,
      right: 24,
      top: isGroupedSeries ? 54 : 26,
      bottom: 56,
      containLabel: true,
    },
    xAxis: isHorizontalBar
      ? {
          type: 'value',
          splitNumber: 5,
          splitLine: {
            lineStyle: {
              color: 'rgba(35, 65, 95, 0.12)',
            },
          },
          axisLine: {
            show: false,
          },
          axisTick: {
            show: false,
          },
          axisLabel: {
            color: '#4f647a',
            formatter(value) {
              return formatAxisMetric(value, isCurrencySeries)
            },
          },
        }
      : {
          type: 'category',
          data: chartConfig.value.labels,
          boundaryGap: !isLine,
          axisTick: {
            show: false,
          },
          axisLine: {
            lineStyle: {
              color: 'rgba(35, 65, 95, 0.28)',
            },
          },
          axisLabel: {
            interval: 0,
            rotate: chartConfig.value.labels.length > 5 ? 18 : 0,
            color: '#4f647a',
            fontWeight: 600,
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
            color: '#4f647a',
            fontWeight: 600,
          },
        }
      : {
          type: 'value',
          splitNumber: 5,
          splitLine: {
            lineStyle: {
              color: 'rgba(35, 65, 95, 0.12)',
            },
          },
          axisLine: {
            show: false,
          },
          axisTick: {
            show: false,
          },
          axisLabel: {
            color: '#4f647a',
            formatter(value) {
              return formatAxisMetric(value, isCurrencySeries)
            },
          },
        },
    series,
  })
  chartInstance.resize()
}

async function validateSession() {
  try {
    const response = await getAuthenticatedUser()
    currentUser.value = response.user
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
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isLoading.value = false
  }
}

function logout() {
  clearAuthSession()
  router.push({ name: 'login' })
}

onMounted(() => {
  validateSession()
})

watch(chartConfig, () => {
  renderChart()
})

onBeforeUnmount(() => {
  disposeChart()
})
</script>

<template>
  <main class="prompt-layout">
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
              {{ result.preview_row_count }} linha(s) retornada(s) para validação rápida.
            </p>
            <div v-if="result.preview_rows?.length" class="table-wrapper">
              <table class="preview-table">
                <thead>
                  <tr>
                    <th v-for="column in previewColumns" :key="column">{{ column }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in result.preview_rows" :key="index">
                    <td v-for="column in previewColumns" :key="column">
                      {{ formatPreviewValue(column, row[column]) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else class="result-caption">
              {{ result.user_message || 'Nenhuma linha foi retornada para este preview.' }}
            </p>
          </article>

          <article v-if="chartConfig && result.preview_row_count" class="result-card result-card--wide">
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

          <article v-if="isAdmin && result.draft_script" class="result-card result-card--wide">
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
}

.prompt-shell {
  max-width: 1100px;
  margin: 0 auto;
  display: grid;
  gap: 1.25rem;
}

.topbar,
.input-card,
.result-card,
.status-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(16, 36, 58, 0.08);
  border-radius: 24px;
  box-shadow: 0 18px 50px rgba(16, 36, 58, 0.08);
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
  color: #1e5d8f;
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
  color: #4f647a;
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
  border: 1px solid rgba(35, 65, 95, 0.18);
  border-radius: 18px;
  background: #f8fbff;
}

.actions,
.topbar {
  display: flex;
}

button {
  border: 0;
  border-radius: 14px;
  padding: 0.85rem 1.1rem;
  font-weight: 800;
  cursor: pointer;
}

.actions button {
  background: #0f2742;
  color: white;
}

.secondary-button {
  background: #edf3f9;
  color: #0f2742;
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
  color: #4f647a;
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
  background: #f5f8fc;
  border: 1px solid rgba(16, 36, 58, 0.08);
}

.field-chip span,
.field-chip small {
  color: #4f647a;
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
  color: #4f647a;
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
  background: #f8fbff;
}

.preview-table th,
.preview-table td {
  padding: 0.9rem 1rem;
  text-align: left;
  border-bottom: 1px solid rgba(16, 36, 58, 0.08);
}

.preview-table th {
  background: #eaf2fb;
  color: #0f2742;
  font-size: 0.9rem;
}

.chart-surface {
  margin-top: 1rem;
  width: 100%;
  min-height: 360px;
  border-radius: 18px;
  padding: 0.5rem;
  background:
    radial-gradient(circle at top left, rgba(30, 93, 143, 0.08), transparent 24%),
    linear-gradient(180deg, #f8fbff 0%, #eef5fc 100%);
}

.result-card--wide {
  grid-column: 1 / -1;
}

@media (max-width: 760px) {
  .topbar,
  .result-grid {
    flex-direction: column;
    grid-template-columns: 1fr;
  }
}
</style>
