# AfterResume Backend

AI-powered work tracking and resume generation system.

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run migrations
python manage.py migrate

# Create admin user
python scripts/create_admin.py

# Run development server
python manage.py runserver

# Run worker (in separate terminal)
python manage.py run_huey

# Run tests
pytest
```

## Environment Variables

```
DJANGO_SETTINGS_MODULE=config.settings.dev
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3  # or postgres://...
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
LLM_PROVIDER=local  # local, vllm
SYSTEM_DASHBOARD_ENABLED=True
```

## Architecture

See `SYSTEM_DESIGN.md` for complete architecture documentation.

### Key Components

- **Domain Apps**: worklog, skills, reporting
- **Job System**: async task execution with Huey
- **Orchestration**: workflows coordinating agents
- **Agents**: AI-powered analysis and generation
- **Observability**: event timeline and structured logging
- **System Dashboard**: operational monitoring API

### API Endpoints

- `/api/worklogs/` - Work log management
- `/api/skills/` - Skill tracking
- `/api/reports/` - Report generation
- `/api/jobs/{id}/` - Job status
- `/system/` - System dashboard (staff only)

## Development

```bash
# Seed demo data
python scripts/seed_demo_data.py

# Run specific tests
pytest tests/test_jobs.py -v

# Format code
black .
ruff check .
```

### Dokploy and Swarm

# backend server ufw rules

```ufw reset
ufw default deny incoming
ufw default allow outgoing

ufw allow from 10.6.0.0/24 to 10.6.0.5 port 22 proto tcp
ufw allow from 10.6.0.0/24 to 10.6.0.5 port 2377 proto tcp
ufw allow from 10.6.0.0/24 to 10.6.0.5 port 7946 proto tcp
ufw allow from 10.6.0.0/24 to 10.6.0.5 port 7946 proto udp
ufw allow from 10.6.0.0/24 to 10.6.0.5 port 4789 proto udp
ufw allow from 10.6.0.0/24 to 10.6.0.5 port 8000 proto tcp

ufw enable```

# node rules:
```
ufw reset
ufw default deny incoming
ufw default allow outgoing

# SSH – WireGuard only
ufw allow from 10.6.0.0/24 to any port 22 proto tcp

# Docker Swarm
ufw allow from 10.6.0.0/24 to any port 2377 proto tcp
ufw allow from 10.6.0.0/24 to any port 7946 proto tcp
ufw allow from 10.6.0.0/24 to any port 7946 proto udp
ufw allow from 10.6.0.0/24 to any port 4789 proto udp

# Public web traffic
ufw allow 80/tcp
ufw allow 443/tcp

ufw enable
```

# Modified Dokploy Script
```#!/bin/bash

install_dokploy() {
    if [ "$(id -u)" != "0" ]; then
        echo "This script must be run as root" >&2
        exit 1
    fi

    if [ "$(uname)" = "Darwin" ]; then
        echo "This script must be run on Linux" >&2
        exit 1
    fi

    if [ -f /.dockerenv ]; then
        echo "This script must be run on Linux (not inside a container)" >&2
        exit 1
    fi

    # Port checks
    for port in 80 443 3000; do
        if ss -tulnp | grep ":$port " >/dev/null; then
            echo "Error: something is already running on port $port" >&2
            exit 1
        fi
    done

    command_exists() {
        command -v "$@" >/dev/null 2>&1
    }

    if command_exists docker; then
        echo "Docker already installed"
    else
        curl -sSL https://get.docker.com | sh
    fi

    # ---- Swarm validation (NO init / leave) ----
    if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
        echo "Error: Docker Swarm is not active on this host." >&2
        echo "Please initialize or join a swarm before installing Dokploy." >&2
        exit 1
    fi

    if ! docker info --format '{{.Swarm.ControlAvailable}}' | grep -q true; then
        echo "Error: This node is not a Swarm manager." >&2
        exit 1
    fi

    advertise_addr="10.6.0.2"
    echo "Using existing swarm (advertise address: $advertise_addr)"

    # ---- Network ----
    if ! docker network ls --format '{{.Name}}' | grep -q '^dokploy-network$'; then
        docker network create --driver overlay --attachable dokploy-network
        echo "dokploy-network created"
    else
        echo "dokploy-network already exists"
    fi

    mkdir -p /etc/dokploy
    chmod 777 /etc/dokploy

    # ---- Core Services ----
    docker service create \
        --name dokploy-postgres \
        --constraint 'node.role==manager' \
        --network dokploy-network \
        --env POSTGRES_USER=dokploy \
        --env POSTGRES_DB=dokploy \
        --env POSTGRES_PASSWORD=amukds4wi9001583845717ad2 \
        --mount type=volume,source=dokploy-postgres,target=/var/lib/postgresql/data \
        postgres:16 || true

    docker service create \
        --name dokploy-redis \
        --constraint 'node.role==manager' \
        --network dokploy-network \
        --mount type=volume,source=dokploy-redis,target=/data \
        redis:7 || true

    docker pull traefik:v3.6.1
    docker pull dokploy/dokploy:latest

    # ---- Dokploy Service ----
    docker service create \
        --name dokploy \
        --replicas 1 \
        --network dokploy-network \
        --mount type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock \
        --mount type=bind,source=/etc/dokploy,target=/etc/dokploy \
        --mount type=volume,source=dokploy,target=/root/.docker \
        --publish published=3000,target=3000,mode=host \
        --update-parallelism 1 \
        --update-order stop-first \
        --constraint 'node.role==manager' \
        -e ADVERTISE_ADDR=$advertise_addr \
        dokploy/dokploy:latest || true

    # ---- Traefik (standalone container) ----
    docker run -d \
        --name dokploy-traefik \
        --restart always \
        -v /etc/dokploy/traefik/traefik.yml:/etc/traefik/traefik.yml \
        -v /etc/dokploy/traefik/dynamic:/etc/dokploy/traefik/dynamic \
        -v /var/run/docker.sock:/var/run/docker.sock:ro \
        -p 80:80/tcp \
        -p 443:443/tcp \
        -p 443:443/udp \
        traefik:v3.6.1 || true

    docker network connect dokploy-network dokploy-traefik || true

    echo ""
    echo "========================================"
    echo " Dokploy installed using existing swarm "
    echo "========================================"
    echo "Access: http://10.6.0.2:3000"
    echo ""
}

update_dokploy() {
    echo "Updating Dokploy..."
    docker pull dokploy/dokploy:latest
    docker service update --image dokploy/dokploy:latest dokploy
    echo "Dokploy updated."
}

if [ "$1" = "update" ]; then
    update_dokploy
else
    install_dokploy
fi
```


# Node Labeling
```
docker node update --label-add role=dokploy borelli
docker node update --label-add role=frontend cassini
docker node update --label-add role=backend turing
```