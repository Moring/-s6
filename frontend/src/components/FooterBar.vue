<template>
  <footer class="footer-bar">
    <div class="status-pill">Tokens: {{ tokensLabel }}</div>
    <div class="afterresume-muted" v-if="updatedAt">Updated {{ updatedAt }}</div>
    <div class="afterresume-muted" v-if="loading">Refreshing...</div>
    <div class="afterresume-muted" v-if="error">{{ error }}</div>
    <div class="footer-spacer"></div>
    <div class="status-pill" :class="{ 'status-pill--alert': isLowBalance }">
      Reserve: {{ reserveLabel }}
    </div>
  </footer>
</template>

<script>
export default {
  name: 'FooterBar',
  props: {
    sessionTokens: {
      type: Number,
      default: 0,
    },
    reserveBalance: {
      type: Number,
      default: null,
    },
    updatedAt: {
      type: String,
      default: null,
    },
    isLowBalance: {
      type: Boolean,
      default: false,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: null,
    },
  },
  computed: {
    tokensLabel() {
      return Number.isFinite(this.sessionTokens) ? this.sessionTokens : 0
    },
    reserveLabel() {
      if (this.reserveBalance === null || this.reserveBalance === undefined) {
        return '--'
      }
      return `$${Number(this.reserveBalance).toFixed(2)}`
    },
  },
}
</script>
