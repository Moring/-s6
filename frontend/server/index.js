import crypto from 'node:crypto'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import express from 'express'
import { createProxyMiddleware } from 'http-proxy-middleware'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const backendOrigin =
  process.env.BACKEND_ORIGIN || process.env.VITE_BACKEND_ORIGIN || 'http://backend-api:8000'
const serviceSecret = process.env.SERVICE_TO_SERVICE_SECRET || ''

const buildServiceToken = () => {
  const timestamp = Math.floor(Date.now() / 1000)
  const message = `service-call:${timestamp}`
  const signature = crypto.createHmac('sha256', serviceSecret).update(message).digest('hex')
  return `${timestamp}:${signature}`
}

const app = express()

app.get('/healthz', (req, res) => {
  res.status(200).send('ok')
})

app.use(
  '/api',
  createProxyMiddleware({
    target: backendOrigin,
    changeOrigin: true,
    secure: false,
    logLevel: 'warn',
    onProxyReq: (proxyReq) => {
      if (serviceSecret) {
        proxyReq.setHeader('X-Service-Token', buildServiceToken())
      }
    },
  })
)

const distPath = path.resolve(__dirname, '../dist')
app.use(express.static(distPath, { index: false }))

app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

const port = Number(process.env.PORT || 3000)
app.listen(port, () => {
  console.log(`AfterResume frontend listening on ${port}`)
})
