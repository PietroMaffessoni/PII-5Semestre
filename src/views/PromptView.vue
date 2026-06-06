<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

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
const theme = ref(document.documentElement.dataset.theme || 'light')
let chartInstance = null
let echartsModule = null

const welcomeLabel = computed(() => currentUser.value?.usuario || 'usuario autenticado')
const currentRole = computed(() => currentUser.value?.role || '')
const isAdmin = computed(() => currentRole.value === 'admin')
const previewColumns = computed(() => {
  if (!result.value?.preview_rows?.length) {
    return []
  }

  return Object.keys(result.value.preview_rows[0])
})
const chartConfig = computed(() => {
  const rows = result.value?.preview_rows || []
  if (!rows.length) {
    return null
  }

  const columns = Object.keys(rows[0])
  const dimensionColumns = columns.filter((column) => {
    if (column === 'mes') {
      return true
    }

    return typeof rows[0][column] === 'string'
  })
  const numericColumns = columns.filter((column) =>
    rows.every((row) => row[column] !== null && row[column] !== '' && !Number.isNaN(Number(row[column]))),
  )

  const categoryColumn = dimensionColumns[0] || columns[0]
  const valueColumn = numericColumns[0]

  if (!categoryColumn || !valueColumn) {
    return null
  }

  return {
    categoryColumn,
    valueColumn,
    categories: rows.map((row) => formatPreviewValue(categoryColumn, row[categoryColumn])),
    seriesData: rows.map((row) => Number(row[valueColumn])),
  }
})
const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
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

async function renderChart() {
  await nextTick()

  if (!chartElement.value || !chartConfig.value) {
    disposeChart()
    return
  }

  if (!echartsModule) {
    echartsModule = await import('echarts')
  }

  if (!chartInstance) {
    chartInstance = echartsModule.init(chartElement.value)
  }

  const isCurrencySeries = chartConfig.value.valueColumn.toLowerCase().includes('valor')
  const isDarkTheme = theme.value === 'dark'
  const chartTextColor = isDarkTheme ? '#f6fbff' : '#10243a'
  const chartMutedColor = isDarkTheme ? '#c4d0dc' : '#4f647a'
  const chartGridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.12)' : 'rgba(16, 36, 58, 0.1)'
  const chartTooltipBg = isDarkTheme ? 'rgba(11, 22, 33, 0.96)' : 'rgba(255, 255, 255, 0.96)'
  const chartTooltipBorder = isDarkTheme ? 'rgba(255, 255, 255, 0.16)' : 'rgba(16, 36, 58, 0.12)'
  chartInstance.setOption({
    animationDuration: 500,
    color: [isDarkTheme ? '#4b1c73' : '#5cb3a1'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: chartTooltipBg,
      borderColor: chartTooltipBorder,
      textStyle: { color: chartTextColor },
      formatter(params) {
        const item = params[0]
        const value = isCurrencySeries
          ? currencyFormatter.format(Number(item.value))
          : Number(item.value).toLocaleString('pt-BR')
        return `${item.axisValue}<br/>${chartConfig.value.valueColumn}: ${value}`
      },
    },
    grid: {
      left: 36,
      right: 24,
      top: 32,
      bottom: 52,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: chartConfig.value.categories,
      axisLine: { lineStyle: { color: chartGridColor } },
      axisTick: { lineStyle: { color: chartGridColor } },
      axisLabel: {
        color: chartMutedColor,
        interval: 0,
        rotate: chartConfig.value.categories.length > 5 ? 20 : 0,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: chartGridColor } },
      splitLine: { lineStyle: { color: chartGridColor } },
      axisLabel: {
        color: chartMutedColor,
        formatter(value) {
          return isCurrencySeries
            ? currencyFormatter.format(Number(value))
            : Number(value).toLocaleString('pt-BR')
        },
      },
    },
    series: [
      {
        name: chartConfig.value.valueColumn,
        type: 'bar',
        barWidth: '52%',
        data: chartConfig.value.seriesData,
        itemStyle: {
          borderRadius: [10, 10, 0, 0],
          color: isDarkTheme ? '#4b1c73' : '#5cb3a1',
        },
      },
    ],
  }, true)
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

function handleThemeChange(event) {
  theme.value = event.detail?.theme || document.documentElement.dataset.theme || 'light'
  renderChart()
}

onMounted(() => {
  window.addEventListener('themechange', handleThemeChange)
  validateSession()
})

watch(chartConfig, () => {
  renderChart()
})

onBeforeUnmount(() => {
  window.removeEventListener('themechange', handleThemeChange)
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

        <section v-if="result" class="result-grid">
          <article v-if="isAdmin" class="result-card">
            <h2>Interpretação da pergunta</h2>
            <ul>
              <li><strong>Dominio:</strong> {{ result.interpretation.domain }}</li>
              <li><strong>Metrica:</strong> {{ result.interpretation.metric }}</li>
              <li><strong>Dimensões:</strong> {{ result.interpretation.dimensions.join(', ') }}</li>
              <li><strong>Período:</strong> últimos {{ result.interpretation.period_months }} meses</li>
              <li><strong>Visual sugerido:</strong> {{ result.interpretation.chart_suggestion }}</li>
            </ul>
          </article>

          <article v-if="isAdmin" class="result-card">
            <h2>Tabelas sugeridas</h2>
            <ul>
              <li v-for="item in result.suggested_tables" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article v-if="isAdmin" class="result-card">
            <h2>Filtros sugeridos</h2>
            <ul>
              <li v-for="item in result.suggested_filters" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article v-if="isAdmin" class="result-card result-card--wide">
            <h2>Campos relevantes</h2>
            <div class="field-grid">
              <div v-for="item in result.relevant_fields" :key="`${item.table}-${item.field}`" class="field-chip">
                <strong>{{ item.table }}.{{ item.field }}</strong>
                <span>{{ item.label }}</span>
                <small>{{ item.description }}</small>
              </div>
            </div>
          </article>

          <article v-if="isAdmin" class="result-card result-card--wide">
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
            <p v-else class="result-caption">Nenhuma linha foi retornada para este preview.</p>
          </article>

          <article v-if="chartConfig" class="result-card result-card--wide">
            <h2>Visualização gráfica</h2>
            <p class="result-caption">
              Gráfico montado a partir das colunas <strong>{{ chartConfig.categoryColumn }}</strong> e
              <strong>{{ chartConfig.valueColumn }}</strong>.
            </p>
            <div ref="chartElement" class="chart-surface"></div>
          </article>

          <article v-if="isAdmin" class="result-card result-card--wide result-card--sql">
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
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 24px;
  box-shadow: var(--panel-shadow);
  transition:
    background 220ms ease,
    border-color 220ms ease,
    box-shadow 220ms ease;
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
  .topbar,
  .result-grid {
    flex-direction: column;
    grid-template-columns: 1fr;
  }
}
</style>
