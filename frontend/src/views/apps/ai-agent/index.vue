<template>
  <MainLayout>
    <BContainer fluid>
      <PageBreadcrumb title="AI Agent Chat" subtitle="Apps" />

      <BRow>
        <BCol cols="12">
          <BCard no-body class="mb-0">
            <BCardBody class="p-0">
              <div class="chat-container">
                <simplebar class="chat-messages" ref="chatMessagesRef" style="max-height: calc(100vh - 250px)">
                  <div v-if="messages.length === 0" class="text-center text-muted py-5">
                    <Icon icon="tabler:message-chatbot" class="fs-1" />
                    <p class="mt-2">Start a conversation with the AI Agent</p>
                    <p class="small">The agent will use RAG context and LangChain to provide intelligent responses</p>
                  </div>

                  <div v-for="message in messages" :key="message.id" class="message" :class="message.role">
                    <div class="message-avatar">
                      <Icon v-if="message.role === 'user'" icon="tabler:user-circle" class="fs-1 text-primary" />
                      <Icon v-else icon="tabler:robot" class="fs-1 text-success" />
                    </div>
                    <div>
                      <div class="message-content" v-html="message.content"></div>
                      <div class="message-meta">
                        {{ message.role === 'user' ? 'You' : 'AI Agent' }} • {{ message.time }}
                        <span v-if="message.tokens"> • {{ message.tokens }} tokens</span>
                        <span v-if="message.cost"> • ${{ message.cost.toFixed(4) }}</span>
                      </div>
                    </div>
                  </div>
                </simplebar>

                <div v-if="isThinking" class="thinking-indicator">
                  <Icon icon="tabler:loader-2" class="spinner-border spinner-border-sm me-2" />
                  Agent is thinking...
                  <div v-if="steps.length > 0" class="mt-2">
                    <div v-for="(step, index) in steps" :key="index" class="step-indicator">
                      <Icon icon="tabler:circle-check" class="me-2" />{{ step }}
                    </div>
                  </div>
                </div>

                <div class="chat-input-container">
                  <div class="input-group">
                    <BFormInput
                      v-model="inputMessage"
                      type="text"
                      placeholder="Type your message..."
                      autocomplete="off"
                      @keypress.enter="sendMessage"
                      :disabled="isThinking"
                    />
                    <BButton variant="primary" @click="sendMessage" :disabled="isThinking">
                      <Icon icon="tabler:send" class="me-1" /> Send
                    </BButton>
                  </div>
                  <div class="mt-2">
                    <small class="text-muted">
                      <Icon icon="tabler:info-circle" class="me-1" />
                      Powered by LangChain | Connected to RAGApps via MCP
                    </small>
                  </div>
                </div>
              </div>
            </BCardBody>
          </BCard>
        </BCol>
      </BRow>
    </BContainer>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { BButton, BFormInput } from 'bootstrap-vue-next'
import simplebar from 'simplebar-vue'
import { Icon } from '@iconify/vue'
import { usePageMeta } from '@/composables/usePageMeta'
import MainLayout from '@/layouts/MainLayout.vue'
import axios from 'axios'

interface Message {
  id: string
  role: 'user' | 'agent'
  content: string
  time: string
  tokens?: number
  cost?: number
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const isThinking = ref(false)
const steps = ref<string[]>([])
const chatMessagesRef = ref<any>(null)

// Get auth token from localStorage
const getAuthToken = () => {
  return localStorage.getItem('authToken') || ''
}

// Scroll to bottom of chat
const scrollToBottom = () => {
  nextTick(() => {
    if (chatMessagesRef.value) {
      const scrollElement = chatMessagesRef.value.scrollElement || chatMessagesRef.value.$el
      if (scrollElement) {
        scrollElement.scrollTop = scrollElement.scrollHeight
      }
    }
  })
}

// Add message to chat
const addMessage = (role: 'user' | 'agent', content: string, meta: { tokens?: number; cost?: number } = {}) => {
  const now = new Date()
  const time = now.toLocaleTimeString()
  
  messages.value.push({
    id: `msg-${Date.now()}-${Math.random()}`,
    role,
    content,
    time,
    tokens: meta.tokens,
    cost: meta.cost
  })
  
  scrollToBottom()
}

// Send message to API
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message || isThinking.value) return

  // Add user message
  addMessage('user', message)
  inputMessage.value = ''

  // Show thinking indicator
  isThinking.value = true
  steps.value = []

  try {
    const authToken = getAuthToken()
    const response = await axios.post(
      '/api/agent/chat/',
      { message },
      {
        headers: {
          'Authorization': `Token ${authToken}`,
          'Content-Type': 'application/json'
        }
      }
    )

    // Hide thinking indicator
    isThinking.value = false

    // Handle link type responses
    if (response.data.type === 'link' && response.data.url) {
      const linkHtml = `<a href="${response.data.url}" target="_blank">${response.data.title || 'Continue here'}</a>`
      addMessage('agent', linkHtml, {})
      return
    }

    // Handle Hugo redirect
    if (response.data.route === 'hugo' && response.data.slug) {
      window.location.href = 'http://localhost:1313/' + response.data.slug
      return
    }

    // Show agent steps
    if (response.data.steps && response.data.steps.length > 0) {
      steps.value = response.data.steps
    }

    // Add agent response
    addMessage('agent', response.data.response, {
      tokens: response.data.tokens_used,
      cost: response.data.cost_usd
    })

  } catch (error: any) {
    isThinking.value = false
    const errorMsg = error.response?.data?.detail || 'Failed to get response'
    addMessage('agent', `❌ Error: ${errorMsg}`, {})
  }
}

usePageMeta('AI Agent Chat')
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
}

.chat-messages {
  padding: 20px;
  background: var(--bs-body-bg);
}

.message {
  margin-bottom: 20px;
  display: flex;
  gap: 12px;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message.agent .message-content {
  background: var(--bs-primary-bg-subtle);
  border: 1px solid var(--bs-primary-border-subtle);
}

.message.user .message-content {
  background: var(--bs-secondary-bg-subtle);
  border: 1px solid var(--bs-secondary-border-subtle);
}

.message-meta {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
  margin-top: 4px;
}

.chat-input-container {
  padding: 16px;
  border-top: 1px solid var(--bs-border-color);
  background: var(--bs-body-bg);
}

.thinking-indicator {
  padding: 12px 16px;
  font-style: italic;
  color: var(--bs-secondary-color);
  border-top: 1px solid var(--bs-border-color);
}

.step-indicator {
  font-size: 0.875rem;
  padding: 8px 12px;
  margin: 8px 0;
  background: var(--bs-info-bg-subtle);
  border-left: 3px solid var(--bs-info);
  border-radius: 4px;
}

.spinner-border {
  animation: spinner-border 0.75s linear infinite;
}

@keyframes spinner-border {
  to {
    transform: rotate(360deg);
  }
}
</style>
