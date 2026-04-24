<script setup>
import { computed, onMounted, ref } from 'vue'
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

const welcomeLabel = computed(() => currentUser.value?.usuario || 'usuario autenticado')

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
    result.value = await generateScript(prompt.value)
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
</script>

<template>
  <main class="prompt-layout">
    <section class="prompt-shell">
      <header class="topbar">
        <div>
          <span class="eyebrow">Assistente autenticado</span>
          <h1>Escreva o prompt para gerar um SQL inicial.</h1>
          <p>Logado como <strong>{{ welcomeLabel }}</strong>.</p>
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
          <article class="result-card">
            <h2>Interpretacao da pergunta</h2>
            <ul>
              <li><strong>Dominio:</strong> {{ result.interpretation.domain }}</li>
              <li><strong>Metrica:</strong> {{ result.interpretation.metric }}</li>
              <li><strong>Dimensoes:</strong> {{ result.interpretation.dimensions.join(', ') }}</li>
              <li><strong>Periodo:</strong> ultimos {{ result.interpretation.period_months }} meses</li>
              <li><strong>Visual sugerido:</strong> {{ result.interpretation.chart_suggestion }}</li>
            </ul>
          </article>

          <article class="result-card">
            <h2>Tabelas sugeridas</h2>
            <ul>
              <li v-for="item in result.suggested_tables" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article class="result-card">
            <h2>Filtros sugeridos</h2>
            <ul>
              <li v-for="item in result.suggested_filters" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article class="result-card result-card--wide">
            <h2>Campos relevantes</h2>
            <div class="field-grid">
              <div v-for="item in result.relevant_fields" :key="`${item.table}-${item.field}`" class="field-chip">
                <strong>{{ item.table }}.{{ item.field }}</strong>
                <span>{{ item.label }}</span>
                <small>{{ item.description }}</small>
              </div>
            </div>
          </article>

          <article class="result-card result-card--wide">
            <h2>Joins sugeridos</h2>
            <ul>
              <li v-for="item in result.join_suggestions" :key="item">{{ item }}</li>
            </ul>
          </article>

          <article class="result-card result-card--wide">
            <h2>SQL inicial</h2>
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
