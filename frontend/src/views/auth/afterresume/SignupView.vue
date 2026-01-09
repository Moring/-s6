<template>
  <div class="auth-page-wrapper d-flex align-items-center justify-content-center min-vh-100 bg-light">
    <BContainer>
      <BRow class="justify-content-center">
        <BCol lg="6" md="8" sm="10">
          <BCard class="shadow-lg border-0">
            <BCardBody class="p-4">
              <!-- Logo -->
              <div class="text-center mb-4">
                <img src="@/assets/images/logo.png" alt="AfterResume" height="40" class="mb-3" />
                <h4 class="fw-bold">Create Account</h4>
                <p class="text-muted">Join AfterResume with your invite code</p>
              </div>

              <!-- Error Alert -->
              <BAlert v-if="error" variant="danger" dismissible @dismissed="clearError" show>
                {{ error }}
              </BAlert>

              <!-- Signup Form -->
              <form @submit.prevent="handleSignup">
                <BFormGroup label="Invite Passkey" label-for="passkey" class="mb-3">
                  <BFormInput
                    id="passkey"
                    v-model="form.passkey"
                    type="text"
                    placeholder="Enter your invite passkey"
                    required
                    :disabled="loading"
                  />
                  <BFormText class="text-muted">
                    You need an invite passkey to create an account
                  </BFormText>
                </BFormGroup>

                <BFormGroup label="Username" label-for="username" class="mb-3">
                  <BFormInput
                    id="username"
                    v-model="form.username"
                    type="text"
                    placeholder="Choose a username"
                    required
                    :disabled="loading"
                  />
                </BFormGroup>

                <BFormGroup label="Email" label-for="email" class="mb-3">
                  <BFormInput
                    id="email"
                    v-model="form.email"
                    type="email"
                    placeholder="Enter your email"
                    required
                    :disabled="loading"
                  />
                </BFormGroup>

                <BFormGroup label="Password" label-for="password" class="mb-3">
                  <BFormInput
                    id="password"
                    v-model="form.password"
                    type="password"
                    placeholder="Choose a strong password"
                    required
                    :disabled="loading"
                  />
                  <BFormText class="text-muted">
                    At least 8 characters with letters and numbers
                  </BFormText>
                </BFormGroup>

                <BFormGroup label="Confirm Password" label-for="confirmPassword" class="mb-3">
                  <BFormInput
                    id="confirmPassword"
                    v-model="form.confirmPassword"
                    type="password"
                    placeholder="Confirm your password"
                    required
                    :disabled="loading"
                  />
                </BFormGroup>

                <BFormCheckbox v-model="form.acceptTerms" class="mb-3">
                  I agree to the
                  <a href="/terms" target="_blank" class="text-decoration-none">Terms of Service</a>
                  and
                  <a href="/privacy" target="_blank" class="text-decoration-none">Privacy Policy</a>
                </BFormCheckbox>

                <BButton
                  type="submit"
                  variant="primary"
                  class="w-100"
                  :disabled="loading || !form.acceptTerms"
                >
                  <span v-if="loading">
                    <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                    Creating account...
                  </span>
                  <span v-else>Create Account</span>
                </BButton>
              </form>

              <!-- Login Link -->
              <div class="text-center mt-4">
                <p class="text-muted mb-0">
                  Already have an account?
                  <router-link to="/auth/login" class="fw-semibold text-decoration-none">
                    Sign In
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
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  passkey: '',
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  acceptTerms: false
})

const loading = ref(false)
const error = ref<string | null>(null)

const clearError = () => {
  error.value = null
  authStore.clearError()
}

const validateForm = (): boolean => {
  if (!form.passkey || !form.username || !form.email || !form.password) {
    error.value = 'Please fill in all required fields'
    return false
  }

  if (form.password !== form.confirmPassword) {
    error.value = 'Passwords do not match'
    return false
  }

  if (form.password.length < 8) {
    error.value = 'Password must be at least 8 characters long'
    return false
  }

  if (!form.acceptTerms) {
    error.value = 'You must accept the Terms of Service and Privacy Policy'
    return false
  }

  return true
}

const handleSignup = async () => {
  if (!validateForm()) {
    return
  }

  loading.value = true
  error.value = null

  try {
    await authStore.signup({
      passkey: form.passkey,
      username: form.username,
      email: form.email,
      password: form.password
    })

    // Redirect to dashboard after successful signup
    router.push('/dashboard')
  } catch (err: any) {
    error.value = err.message || 'Signup failed. Please check your information.'
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
