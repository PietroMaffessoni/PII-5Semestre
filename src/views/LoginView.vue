<script setup>
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { login } from '../services/api'
import { saveAuthSession } from '../services/auth'

const router = useRouter()
const form = reactive({
  usuario: '',
  senha: '',
})
const errorMessage = ref('')
const isSubmitting = ref(false)
const theme = ref(document.documentElement.dataset.theme || window.localStorage.getItem('theme') || 'light')
const isDarkTheme = computed(() => theme.value === 'dark')

async function handleSubmit() {
  errorMessage.value = ''
  isSubmitting.value = true

  try {
    const response = await login(form)

    saveAuthSession(response)
    router.push({ name: 'prompt' })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    isSubmitting.value = false
  }
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

</script>

<template>
  <main class="login-layout">
    <section class="login-panel">
      <div class="brand-block">
        <span class="eyebrow">ASSISTENTE INTELIGENTE DE DADOS</span>
        <h1>Seus dados transformados em dashboards, em segundos.</h1>
        <p>
          Faça login para acessar a IA. Digite o que você precisa analisar em texto simples e o assistente gera os gráficos visuais para você no Power BI.
        </p>
        <p class="supabase-status">Termos de Uso e Política de Privacidade.</p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <button type="button" class="login-theme-toggle" :aria-pressed="isDarkTheme" @click="toggleTheme">
          <span class="login-theme-toggle__icon" aria-hidden="true"></span>
          {{ isDarkTheme ? 'Claro' : 'Escuro' }}
        </button>

        <label>
          <span>Usuário</span>
          <input v-model.trim="form.usuario" type="text" name="usuario" autocomplete="username" required>
        </label>

        <label>
          <span>Senha</span>
          <input
            v-model="form.senha"
            type="password"
            name="senha"
            autocomplete="current-password"
            required
          >
        </label>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <button type="submit" :disabled="isSubmitting">
          {{ isSubmitting ? 'Validando acesso...' : 'Entrar' }}
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.login-layout {
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 1rem;
}

.login-panel {
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(300px, 0.9fr);
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: var(--panel-shadow);
  transition:
    background 220ms ease,
    border-color 220ms ease,
    box-shadow 220ms ease;
}

.brand-block {
  padding: 2.5rem 2rem;
  background: var(--brand-gradient);
  color: #f7fafc;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 1rem;
  color: rgba(255, 255, 255, 0.98);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
}

.brand-block h1 {
  margin: 0;
  font-size: clamp(1.75rem, 5vw, 2.75rem);
  line-height: 1.1;
}

.brand-block p {
  margin: 1.25rem 0 0;
  max-width: 34rem;
  color: rgba(247, 250, 252, 0.92);
  line-height: 1.6;
  font-size: 0.95rem;
}

.supabase-status {
  margin-top: 1.5rem;
  padding: 0.8rem 0.95rem;
  border-radius: 14px;
  background: var(--brand-soft);
  color: rgba(255, 255, 255, 0.92);
  font-size: 0.85rem;
}

.login-form {
  position: relative;
  display: grid;
  gap: 1.25rem;
  padding: 7rem 2rem 2.5rem;
  align-content: center;
}

.login-theme-toggle {
  position: absolute;
  top: 1.25rem;
  right: 2rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 2.55rem;
  padding: 0.65rem 0.9rem;
  border: 1px solid transparent;
  border-radius: 999px;
  background:
    var(--secondary-button-surface) padding-box,
    var(--button-border) border-box;
  color: var(--secondary-button-text);
  box-shadow: var(--button-shadow);
  font-weight: 800;
  cursor: pointer;
  backdrop-filter: blur(18px) saturate(1.2);
}

.login-theme-toggle__icon {
  flex: 0 0 0.9rem;
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 999px;
  background: currentColor;
  box-shadow: inset -0.28rem -0.16rem 0 rgba(255, 248, 224, 0.9);
}

:global(:root[data-theme='dark']) .login-theme-toggle__icon {
  box-shadow: 0 0 0 0.2rem rgba(255, 255, 255, 0.12);
}

.login-form label {
  display: grid;
  gap: 0.5rem;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.9rem;
}

.login-form input {
  width: 100%;
  padding: 0.85rem 1rem;
  border: 1px solid var(--input-border);
  border-radius: 14px;
  background: var(--input-bg);
  color: var(--text-primary);
  font-size: 1rem;
}

.login-form button[type='submit'] {
  margin-top: 0.5rem;
  border: 1px solid transparent;
  border-radius: 14px;
  padding: 1rem;
  background:
    var(--button-surface) padding-box,
    var(--button-border) border-box;
  color: var(--button-text);
  box-shadow: var(--button-shadow);
  font-weight: 800;
  cursor: pointer;
  backdrop-filter: blur(16px) saturate(1.18);
  font-size: 1rem;
}

.login-form button[type='submit']:disabled {
  opacity: 0.7;
  cursor: progress;
}

.error-message {
  margin: 0;
  color: #b42318;
  font-size: 0.85rem;
  text-align: center;
}

@media (max-width: 860px) {
  .login-panel {
    grid-template-columns: 1fr;
  }

  .brand-block {
    padding: 2rem 1.5rem;
  }

  .login-form {
    padding: 6.5rem 1.5rem 2rem;
  }

  .login-theme-toggle {
    right: 1.5rem;
  }
}

@media (max-width: 480px) {
  .login-layout {
    padding: 0.75rem;
    padding-top: 4.25rem;
    min-height: 100svh;
    place-items: start center;
  }

  .login-panel {
    width: 100%;
    border-radius: 18px;
  }

  .brand-block,
  .login-form {
    padding: 1.15rem;
  }

  .login-form {
    padding-top: 4.8rem;
  }

  .login-theme-toggle {
    top: 1rem;
    right: 1rem;
    min-height: 2.35rem;
    padding: 0.55rem 0.7rem;
    font-size: 0.9rem;
  }

  .eyebrow {
    margin-bottom: 0.7rem;
    font-size: 0.72rem;
    letter-spacing: 0.04em;
  }

  .brand-block h1 {
    font-size: clamp(1.45rem, 7vw, 1.85rem);
    line-height: 1.14;
  }

  .brand-block p {
    margin-top: 0.75rem;
    line-height: 1.5;
    font-size: 0.95rem;
  }

  .supabase-status {
    margin-top: 0.9rem;
    padding: 0.7rem 0.8rem;
    border-radius: 12px;
  }

  .login-form {
    gap: 0.85rem;
  }

  .login-form input,
  .login-form button[type='submit'] {
    padding: 0.82rem 0.9rem;
    border-radius: 12px;
  }

  .login-form button[type='submit'] {
    min-height: 2.9rem;
  }

  .error-message {
    font-size: 0.9rem;
  }
}

@media (max-width: 360px) {
  .login-layout {
    padding: 0.55rem;
    padding-top: 3.9rem;
  }

  .brand-block,
  .login-form {
    padding: 0.95rem;
  }

  .login-form {
    padding-top: 4.4rem;
  }

  .login-theme-toggle {
    right: 0.85rem;
    gap: 0.35rem;
    padding: 0.5rem 0.62rem;
    font-size: 0.82rem;
  }

  .brand-block h1 {
    font-size: 1.35rem;
  }

  .brand-block p,
  .login-form label {
    font-size: 0.9rem;
  }

  .login-form input,
  .login-form button[type='submit'] {
    padding: 0.74rem 0.78rem;
    font-size: 0.92rem;
  }
}
</style>
