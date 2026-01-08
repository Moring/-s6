import { createRouter, createWebHistory } from 'vue-router'
import { allRoutes } from '@/router/routes.ts'
import { appTitle } from '@/helpers'
import authService from '@/services/auth.service'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: allRoutes,
})

// Public routes that don't require authentication
const publicRoutes = ['/auth/login', '/auth/signup', '/auth/reset-password']

router.beforeEach((to, from, next) => {
  // Set page title
  const title = to.meta.title ? to.meta.title + ' | ' + appTitle : appTitle
  if (title) {
    document.title = title.toString()
  }

  // Check authentication for protected routes
  const isPublicRoute = publicRoutes.some(route => to.path.startsWith(route))
  const isAuthenticated = authService.isAuthenticated()

  if (!isPublicRoute && !isAuthenticated) {
    // Redirect to login with return URL
    next({
      path: '/auth/login',
      query: { redirect: to.fullPath }
    })
  } else if (isPublicRoute && isAuthenticated && to.path.startsWith('/auth/login')) {
    // If already logged in and trying to access login, redirect to dashboard
    next('/dashboard')
  } else {
    next()
  }
})

export default router
