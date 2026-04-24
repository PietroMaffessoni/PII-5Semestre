<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { login } from '../services/api'
import { saveAuthSession } from '../services/auth'
import { supabase } from '../utils/supabase'

const router = useRouter()
const form = reactive({
  usuario: '',
  senha: '',
})
const errorMessage = ref('')
const isSubmitting = ref(false)
const supabaseStatus = ref('Verificando cliente Supabase...')

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

async function checkSupabaseClient() {
  const { error } = await supabase.auth.getSession()
  supabaseStatus.value = error
    ? 'Falha ao inicializar o cliente Supabase.'
    : 'Cliente Supabase configurado para o frontend.'
}

onMounted(() => {
  checkSupabaseClient()
})
</script>

<template>
  <main class="login-layout">
    <section class="login-panel">
      <div class="brand-block">
        <span class="eyebrow">Geracao de SQL para Power BI</span>
        <h1>Entre com uma conta valida para acessar o assistente.</h1>
        <p>
          O acesso ao prompt e liberado apenas para usuarios autenticados na base PostgreSQL.
        </p>
        <p class="supabase-status">{{ supabaseStatus }}</p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label>
          <span>Usuario</span>
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
  padding: 1.25rem;
}

.login-panel {
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(16, 36, 58, 0.08);
  border-radius: 28px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(16, 36, 58, 0.12);
}

.brand-block {
  padding: 2rem;
  background: linear-gradient(135deg, #0f2742 0%, #1e5d8f 100%);
  color: #f7fafc;
}

.eyebrow {
  display: inline-block;
  margin-bottom: 1rem;
  color: #bfd5ea;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.brand-block h1 {
  margin: 0;
  font-size: clamp(2rem, 3vw, 3rem);
  line-height: 1.05;
}

.brand-block p {
  margin: 1rem 0 0;
  max-width: 34rem;
  color: rgba(247, 250, 252, 0.82);
  line-height: 1.7;
}

.supabase-status {
  margin-top: 1.25rem;
  padding: 0.8rem 0.95rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  color: #d9ebfb;
}

.login-form {
  display: grid;
  gap: 1rem;
  padding: 2rem;
  align-content: center;
}

.login-form label {
  display: grid;
  gap: 0.45rem;
  color: #23415f;
  font-weight: 600;
}

.login-form input {
  width: 100%;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(35, 65, 95, 0.18);
  border-radius: 14px;
  background: #f8fbff;
}

.login-form button {
  border: 0;
  border-radius: 14px;
  padding: 0.95rem 1rem;
  background: #f5b700;
  color: #0f2742;
  font-weight: 800;
  cursor: pointer;
}

.login-form button:disabled {
  opacity: 0.7;
  cursor: progress;
}

.error-message {
  margin: 0;
  color: #b42318;
  font-size: 0.95rem;
}

@media (max-width: 860px) {
  .login-panel {
    grid-template-columns: 1fr;
  }
}
</style>
