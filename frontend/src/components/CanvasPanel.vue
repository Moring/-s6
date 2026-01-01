<template>
  <section class="afterresume-panel canvas-panel">
    <div class="panel-header">
      <div>
        <div class="panel-title">Canvas</div>
        <div class="panel-subtitle">Structured output appears here.</div>
      </div>
      <div class="afterresume-muted">{{ updatedLabel }}</div>
    </div>
    <div class="canvas-body">
      <div v-if="canvas.type === 'welcome'" class="canvas-card">
        <h4>Welcome to AfterResume</h4>
        <p class="afterresume-muted">
          Use the chat to authenticate or run admin actions. The canvas will summarize results
          and next steps.
        </p>
      </div>

      <div v-else-if="canvas.type === 'loading'" class="canvas-card">
        <h4>{{ canvas.payload.title || 'Working on it...' }}</h4>
        <p class="afterresume-muted">Hold tight while we contact the backend.</p>
      </div>

      <div v-else-if="canvas.type === 'dashboard'" class="canvas-card">
        <h4>Dashboard</h4>
        <p class="afterresume-muted">Session overview for {{ canvas.payload.user.username }}.</p>
        <div class="row mt-3">
          <div class="col-md-6">
            <div class="status-pill">User: {{ canvas.payload.user.username }}</div>
          </div>
          <div class="col-md-6">
            <div class="status-pill">Tenant: {{ canvas.payload.user.profile?.tenant_name || '--' }}</div>
          </div>
          <div class="col-md-6 mt-2">
            <div class="status-pill">Tokens: {{ canvas.payload.sessionTokens }}</div>
          </div>
          <div class="col-md-6 mt-2">
            <div class="status-pill">Reserve: {{ formatReserve(canvas.payload.reserveBalance) }}</div>
          </div>
        </div>
      </div>

      <div v-else-if="canvas.type === 'auth-error'" class="canvas-card">
        <h4>Authentication Issue</h4>
        <p class="afterresume-muted">{{ canvas.payload.message }}</p>
      </div>

      <div v-else-if="canvas.type === 'not-authorized'" class="canvas-card">
        <h4>Not Authorized</h4>
        <p class="afterresume-muted">{{ canvas.payload.message }}</p>
      </div>

      <div v-else-if="canvas.type === 'not-logged-in'" class="canvas-card">
        <h4>Login Required</h4>
        <p class="afterresume-muted">{{ canvas.payload.message }}</p>
      </div>

      <div v-else-if="canvas.type === 'admin-passkey'" class="canvas-card">
        <h4>Invite Passkey Created</h4>
        <p class="afterresume-muted">Share this once. It will not be shown again.</p>
        <div class="status-pill">Raw Key: {{ canvas.payload.rawKey }}</div>
        <pre class="mt-3">{{ formatJson(canvas.payload.passkey) }}</pre>
      </div>

      <div v-else-if="canvas.type === 'admin-users'" class="canvas-card">
        <h4>User Directory</h4>
        <table class="canvas-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Active</th>
              <th>Role</th>
              <th>Tenant</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>{{ user.id }}</td>
              <td>{{ user.username }}</td>
              <td>{{ user.email }}</td>
              <td>{{ user.is_active ? 'Yes' : 'No' }}</td>
              <td>{{ user.is_staff ? 'Admin' : 'User' }}</td>
              <td>{{ user.profile?.tenant_name || '--' }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="canvas.type === 'admin-user'" class="canvas-card">
        <h4>User Profile</h4>
        <pre>{{ formatJson(canvas.payload.user) }}</pre>
      </div>

      <div v-else-if="canvas.type === 'admin-update'" class="canvas-card">
        <h4>User Updated</h4>
        <p class="afterresume-muted">{{ canvas.payload.message }}</p>
        <pre>{{ formatJson(canvas.payload.user) }}</pre>
      </div>

      <div v-else-if="canvas.type === 'admin-reset'" class="canvas-card">
        <h4>Password Reset</h4>
        <p class="afterresume-muted">{{ canvas.payload.message }}</p>
      </div>

      <div v-else-if="canvas.type === 'admin-help'" class="canvas-card">
        <h4>Admin Commands</h4>
        <ul>
          <li>create passkey expires=YYYY-MM-DD tenant=ID max_uses=1 notes="text"</li>
          <li>list users search=term is_active=true</li>
          <li>enable user USER_ID</li>
          <li>disable user USER_ID reason="text"</li>
          <li>reset password USER_ID NEW_PASSWORD</li>
          <li>view user USERNAME_OR_EMAIL</li>
          <li>update user USER_ID stripe_customer_id=ID notes="text"</li>
        </ul>
      </div>

      <div v-else class="canvas-card">
        <h4>Activity</h4>
        <p class="afterresume-muted">Waiting for the next command.</p>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: 'CanvasPanel',
  props: {
    canvas: {
      type: Object,
      required: true,
    },
    updatedAt: {
      type: String,
      default: null,
    },
  },
  computed: {
    updatedLabel() {
      if (!this.updatedAt) {
        return ''
      }
      return `Updated ${new Date(this.updatedAt).toLocaleTimeString()}`
    },
    users() {
      return Array.isArray(this.canvas.payload.users) ? this.canvas.payload.users : []
    },
  },
  methods: {
    formatReserve(value) {
      if (value === null || value === undefined) {
        return '--'
      }
      return `$${Number(value).toFixed(2)}`
    },
    formatJson(value) {
      return JSON.stringify(value, null, 2)
    },
  },
}
</script>
