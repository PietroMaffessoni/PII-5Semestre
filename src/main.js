import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

function installAndroidInputFocusFix() {
  const editableSelector = 'input, textarea, [contenteditable="true"]'

  const focusEditable = (target) => {
    const editable = target?.closest?.(editableSelector)

    if (!editable || editable.disabled || editable.readOnly) {
      return
    }

    editable.focus({ preventScroll: true })

    window.setTimeout(() => {
      editable.focus({ preventScroll: true })
    }, 50)
  }

  document.addEventListener('pointerdown', (event) => focusEditable(event.target), true)

  window.addEventListener('pageshow', () => {
    const activeElement = document.activeElement

    if (activeElement?.matches?.(editableSelector)) {
      window.setTimeout(() => focusEditable(activeElement), 100)
    }
  })
}

installAndroidInputFocusFix()

const app = createApp(App)

app.use(router)

app.mount('#app')
