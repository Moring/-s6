<template>
  <div class="auth-page-wrapper d-flex align-items-center justify-content-center min-vh-100 bg-light">
    <BContainer>
      <BRow class="justify-content-center">
        <BCol lg="5" md="7" sm="10">
          <BCard class="shadow-lg border-0">
            <BCardBody class="p-4">
              <!-- Logo -->
              <div class="text-center mb-4">
                <img src="@/assets/images/logo.png" alt="AfterResume" height="40" class="mb-3" />
                <h4 class="fw-bold">Sign In</h4>
                <p class="text-muted">Welcome back! Please sign in to continue.</p>
              </div>

              <!-- Error Alert -->
              <BAlert v-if="error" variant="danger" dismissible @dismissed="clearError" show>
                {{ error }}
              </BAlert>

              <!-- Success message after signup -->
              <BAlert v-if="route.query.signup === 'success'" variant="success" show>
                Account created successfully! Please sign in.
              </BAlert>

              <!-- Login Form -->
              <form @submit.prevent="handleLogin">
                <BFormGroup label="Username" label-for="username" class="mb-3">
                  <BFormInput
                    id="username"
                    v-model="form.username"
                    type="text"
                    placeholder="Enter username"
                    required
                    :disabled="loading"
                  />
                </BFormGroup>

                <BFormGroup label="Password" label-for="password" class="mb-3">
                  <BFormInput
                    id="password"
                    v-model="form.password"
                    type="password"
                    placeholder="Enter password"
                    required
                    :disabled="loading"
                  />
                </BFormGroup>

                <div class="d-flex justify-content-between align-items-center mb-3">
                  <BFormCheckbox v-model="form.rememberMe">
                    Remember me
                  </BFormCheckbox>
                  <router-link to="/auth/reset-password" class="text-decoration-none">
                    Forgot password?
                  </router-link>
                </div>

                <BButton
                  type="submit"
                  variant="primary"
                  class="w-100"
                  :disabled="loading"
                >
                  <span v-if="loading">
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Signing in...
                  </span>
                  <span v-else>Sign In</span>
                </BButton>
              </form>

              <!-- Signup Link -->
              <div class="text-center mt-4">
                <p class="text-muted mb-0">
                  Don't have an account?
                  <router-link to="/auth/signup" class="fw-semibold text-decoration-none">
                    Sign Up
                  </router-link>
                </p>
              </div>
            </BCardBody>
          </BCard>
        </BCol>
      </BRow>
    </BContainer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
  rememberMe: false
})

const loading = ref(false)
const error = ref<string | null>(null)

const clearError = () => {
  error.value = null
  authStore.clearError()
}

const handleLogin = async () => {
  if (!form.username || !form.password) {
    error.value = 'Please enter both username and password'
    return
  }

  loading.value = true
  error.value = null

  try {
    await authStore.login({
      username: form.username,
      password: form.password
    })

    // Redirect to intended page or dashboard
    const redirect = route.query.redirect as string || '/dashboard'
    router.push(redirect)
  } catch (err: any) {
    error.value = err.message || 'Login failed. Please check your credentials.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page-wrapper {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
