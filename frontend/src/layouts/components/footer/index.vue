<template>
  <footer class="footer">
    <BContainer fluid>
      <BRow>
        <BCol md="6" class="text-center text-md-start">
          © {{ currentYear }} DigiMuse.AI
        </BCol>
        <BCol md="6">
          <div class="text-md-end d-none d-md-block">
            <span 
              class="clickable-status" 
              @click="showHealthCheck" 
              style="cursor: pointer;"
              title="Click to view system health"
            >
              <span v-if="loading">Loading...</span>
              <span v-else>
                <strong>{{ tokensTotal.toLocaleString() }}</strong> tokens | 
                <strong>${{ reserveBalance }}</strong> reserve
              </span>
            </span>
          </div>
        </BCol>
      </BRow>
    </BContainer>

    <!-- Health Check Modal -->
    <BModal v-model="healthModalVisible" title="System Health" size="lg" hide-footer>
      <div v-if="healthLoading" class="text-center py-4">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
      </div>
      <pre v-else class="bg-light p-3 rounded" style="max-height: 500px; overflow-y: auto;">{{ healthData }}</pre>
      <div class="mt-3 text-end">
        <BButton variant="secondary" @click="healthModalVisible = false">Close</BButton>
      </div>
    </BModal>
  </footer>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { currentYear } from '@/helpers/index.js'
import { systemService } from '@/services/system.service'

const loading = ref(true)
const tokensTotal = ref(0)
const reserveBalance = ref('0.00')
const healthModalVisible = ref(false)
const healthLoading = ref(false)
const healthData = ref('')

let refreshInterval: ReturnType<typeof setInterval> | null = null

const fetchStatusBar = async () => {
  try {
    const data = await systemService.getStatusBar()
    tokensTotal.value = (data.tokens_in || 0) + (data.tokens_out || 0)
    reserveBalance.value = data.reserve_balance_dollars || '0.00'
    loading.value = false
  } catch (error) {
    console.error('Failed to fetch status bar:', error)
    loading.value = false
  }
}

const showHealthCheck = async () => {
  healthModalVisible.value = true
  healthLoading.value = true
  try {
    const data = await systemService.getReadyz()
    healthData.value = JSON.stringify(data, null, 2)
  } catch (error) {
    healthData.value = JSON.stringify({ error: 'Failed to fetch health check' }, null, 2)
  } finally {
    healthLoading.value = false
  }
}

onMounted(() => {
  fetchStatusBar()
  // Refresh every 30 seconds
  refreshInterval = setInterval(fetchStatusBar, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.clickable-status:hover {
  text-decoration: underline;
}
</style>
