---
title: Docker Setup
description: Run AgentLens with Docker or Docker Compose
---

## Docker Run (Quickest)

```bash
docker run -p 3000:3000 tranhoangtu/agentlens-observe:0.5.0
```

Data is stored in-container (lost on restart). For persistence, mount a volume:

```bash
docker run -p 3000:3000 \
  -v agentlens-data:/app/data \
  tranhoangtu/agentlens-observe:0.5.0
```

## Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  agentlens:
    image: tranhoangtu/agentlens-observe:0.5.0
    ports:
      - "3000:3000"
    volumes:
      - agentlens-data:/app/data
    environment:
      - AGENTLENS_JWT_SECRET=your-secret-here
      - AGENTLENS_ADMIN_EMAIL=admin@yourcompany.com
      - AGENTLENS_ADMIN_PASSWORD=strongpassword
    restart: unless-stopped

volumes:
  agentlens-data:
```

```bash
docker compose up -d
```

## With PostgreSQL

For production workloads, use PostgreSQL instead of SQLite:

```yaml
version: '3.8'

services:
  agentlens:
    image: tranhoangtu/agentlens-observe:0.5.0
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://agentlens:password@db:5432/agentlens
      - AGENTLENS_JWT_SECRET=your-secret-here
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=agentlens
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=agentlens
    volumes:
      - pg-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pg-data:
```

## Building from Source

```bash
git clone https://github.com/tranhoangtu-it/agentlens
cd agentlens
docker build -t agentlens-local .
docker run -p 3000:3000 agentlens-local
```

## Health Check

```bash
curl http://localhost:3000/api/health
# → {"status": "ok"}
```
