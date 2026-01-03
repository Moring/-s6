<template>
  <section class="afterresume-panel chat-panel">
    <div class="panel-header">
      <div>
        <div class="panel-title">Chat</div>
        <div class="panel-subtitle">Respond to the prompts to continue.</div>
      </div>
      <div class="afterresume-muted">{{ statusLabel }}</div>
    </div>
    <transition-group ref="messages" tag="div" name="message" class="chat-messages">
      <div
        v-for="message in messages"
        :key="message.id"
        :class="['chat-message', message.role === 'user' ? 'chat-message--user' : 'chat-message--assistant']"
      >
        <div v-if="message.role !== 'user'" class="afterresume-muted">AfterResume</div>
        <div>{{ message.text }}</div>
      </div>
    </transition-group>
    <form class="chat-input" @submit.prevent="submit">
      <textarea
        v-model="draft"
        class="form-control"
        rows="2"
        :disabled="busy"
        placeholder="Type your response..."
      ></textarea>
      <div class="chat-actions">
        <button type="submit" class="btn btn-primary" :disabled="busy || !draft.trim()">
          Send
        </button>
        <span class="afterresume-muted" v-if="busy">Working...</span>
        <span class="afterresume-muted" v-else>Need access? Ask an admin for a passkey.</span>
      </div>
    </form>
  </section>
</template>

<script>
export default {
  name: 'ChatPanel',
  props: {
    messages: {
      type: Array,
      required: true,
    },
    busy: {
      type: Boolean,
      default: false,
    },
    statusLabel: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      draft: '',
    }
  },
  updated() {
    this.scrollToBottom()
  },
  mounted() {
    this.scrollToBottom()
  },
  methods: {
    submit() {
      const value = this.draft.trim()
      if (!value || this.busy) {
        return
      }
      this.$emit('send', value)
      this.draft = ''
    },
    scrollToBottom() {
      const container = this.$refs.messages
      if (container && container.$el) {
        container.$el.scrollTop = container.$el.scrollHeight
      }
    },
  },
}
</script>
