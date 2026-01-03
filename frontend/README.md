# AfterResume Frontend (Vue SPA)

Chat-first Vue single-page app that proxies API requests to the backend over `/api/*`.

## Requirements

- Node.js 18+
- Backend reachable via WireGuard (or localhost for dev)
- `BACKEND_ORIGIN` and `SERVICE_TO_SERVICE_SECRET` set in `.env` (local) or `dokploy.env` (Dokploy)

## Local Development

```bash
npm install
npm run dev
```

The dev server proxies `/api/*` to `BACKEND_ORIGIN` and injects `X-Service-Token`.

## Build + Run (Production)

```bash
npm run build
npm run start
```

`npm run start` serves `dist/` and proxies `/api/*` to the backend with service auth.

## Tests + Lint

```bash
npm test
npm run lint
```
