import { fileURLToPath, URL } from 'node:url'
import crypto from 'node:crypto'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue2'

const buildServiceToken = (secret: string) => {
  const timestamp = Math.floor(Date.now() / 1000)
  const message = `service-call:${timestamp}`
  const signature = crypto.createHmac('sha256', secret).update(message).digest('hex')
  return `${timestamp}:${signature}`
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendOrigin = env.BACKEND_ORIGIN || env.VITE_BACKEND_ORIGIN || 'http://localhost:8000'
  const serviceSecret = env.SERVICE_TO_SERVICE_SECRET || ''

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      port: 3000,
      strictPort: true,
      proxy: {
        '/api': {
          target: backendOrigin,
          changeOrigin: true,
          secure: false,
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              if (serviceSecret) {
                proxyReq.setHeader('X-Service-Token', buildServiceToken(serviceSecret))
              }
            })
          },
        },
      },
    },
  }
})
