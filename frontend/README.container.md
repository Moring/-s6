# Frontend container usage

Build the production image (from repo root):

```bash
docker build -f frontend/Dockerfile.prod -t inspinia-frontend:prod ./frontend
```

Run locally:

```bash
docker run --rm -p 8080:80 \
  -e BACKEND_BASE_URL=http://backend-api:8000 \
  inspinia-frontend:prod
```

Or use docker-compose (from `frontend` directory):

```bash
docker compose up --build
```

Notes:
- The compose file exposes the site on http://localhost:8080.
- Provide a `.env` file in `frontend/` to set `BACKEND_BASE_URL` if needed.
