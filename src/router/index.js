import { createRouter, createWebHistory } from 'vue-router'

import { getAuthToken } from '../services/auth'

const LoginView = () => import('../views/LoginView.vue')
const PromptView = () => import('../views/PromptView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: () => (getAuthToken() ? '/prompt' : '/login'),
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/prompt',
      name: 'prompt',
      component: PromptView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach((to) => {
  const token = getAuthToken()

  if (to.meta.requiresAuth && !token) {
    return { name: 'login' }
  }

  if (to.meta.guestOnly && token) {
    return { name: 'prompt' }
  }

  return true
})

export default router
