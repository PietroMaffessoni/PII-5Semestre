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

function handleWindowResize() {
  chartInstance?.resize()
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

  const isCurrencySeries = chartConfig.value.valueColumn.toLowerCase().includes('valor')
  chartInstance.setOption({
    animationDuration: 500,
    color: ['#1e5d8f'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
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
      axisLabel: {
        interval: 0,
        rotate: chartConfig.value.categories.length > 5 ? 20 : 0,
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
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
        },
      },
    ],
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
  window.addEventListener('resize', handleWindowResize)
})

watch(chartConfig, () => {
  renderChart()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleWindowResize)
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
        <p>Validando autenticacao...</p>
      </section>

      <template v-else>
        <section class="input-card">
          <label for="prompt">Prompt de comando</label>
          <textarea
            id="prompt"
            v-model.trim="prompt"
            rows="8"
            placeholder="Ex.: Quero o volume de producao por planta nos ultimos 3 meses para montar um grafico no Power BI."
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
            <h2>Interpretacao da pergunta</h2>
            <ul>
              <li><strong>Dominio:</strong> {{ result.interpretation.domain }}</li>
              <li><strong>Metrica:</strong> {{ result.interpretation.metric }}</li>
              <li><strong>Dimensoes:</strong> {{ result.interpretation.dimensions.join(', ') }}</li>
              <li><strong>Periodo:</strong> ultimos {{ result.interpretation.period_months }} meses</li>
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
              {{ result.preview_row_count }} linha(s) retornada(s) para validacao rapida.
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
            <h2>Visualizacao grafica</h2>
            <p class="result-caption">
              Grafico montado a partir das colunas <strong>{{ chartConfig.categoryColumn }}</strong> e
              <strong>{{ chartConfig.valueColumn }}</strong>.
            </p>
            <div ref="chartElement" class="chart-surface"></div>
          </article>

          <article v-if="isAdmin" class="result-card result-card--wide">
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
  padding: clamp(0.75rem, 2vw, 1.5rem);
  background:
    radial-gradient(circle at top right, rgba(30, 93, 143, 0.08), transparent 28%),
    linear-gradient(180deg, #f8fbff 0%, #f1f6fb 100%);
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
  padding: clamp(1.1rem, 3vw, 1.5rem);
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
  padding: clamp(1rem, 3vw, 1.5rem);
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
  min-height: 10rem;
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

.actions {
  justify-content: flex-start;
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
  white-space: pre-wrap;
  word-break: break-word;
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
  min-width: 640px;
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
  background: linear-gradient(180deg, #f8fbff 0%, #eef5fc 100%);
}

.result-card--wide {
  grid-column: 1 / -1;
}

@media (max-width: 760px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }

  .secondary-button,
  .actions button {
    width: 100%;
  }

  .chart-surface {
    min-height: 300px;
  }
}

@media (max-width: 560px) {
  .prompt-layout {
    padding: 0.5rem;
  }

  .topbar,
  .input-card,
  .result-card,
  .status-card {
    border-radius: 20px;
  }

  .topbar h1 {
    font-size: 1.7rem;
    line-height: 1.15;
  }

  .input-card textarea,
  .preview-table th,
  .preview-table td,
  .result-card pre {
    font-size: 0.95rem;
  }

  .field-grid {
    grid-template-columns: 1fr;
  }

  .preview-table {
    min-width: 560px;
  }

  .chart-surface {
    min-height: 260px;
  }
}
</style>
