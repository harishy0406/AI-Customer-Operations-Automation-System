# AI Customer Operations Automation System

Enterprise-grade LLM-powered customer support platform with Retrieval-Augmented Generation (RAG), hallucination detection, semantic caching, and production-grade observability.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-00a86b.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.3%2B-316192.svg)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Architecture

<img width="1536" height="1024" alt="ChatGPT Image Jul 6, 2026, 12_14_25 AM" src="https://github.com/user-attachments/assets/ea5aff48-eb3c-4994-a74d-34aad40213ed" />


## Features

- **RAG-Powered Q&A** — Hybrid search (vector + BM25) with reciprocal rank fusion re-ranking
- **Hallucination Detection** — LLM-as-judge groundedness scoring with 3-tier threshold routing (auto-send / flag / withhold)
- **Semantic Caching** — Redis-backed cosine similarity cache with `kb_version` invalidation
- **Multi-Tenant** — Tenant-isolated data with JWT auth and RBAC (customer, agent, ops_manager, admin)
- **Streaming Responses** — Server-Sent Events (SSE) for real-time chat UX
- **Pluggable LLM Providers** — OpenAI, Anthropic, Groq via abstraction layer
- **Document Ingestion** — PDF, Markdown, HTML, CSV with token-aware chunking
- **Prompt Evaluation Framework** — Golden dataset regression testing with pass/fail metrics
- **Observability** — Prometheus metrics, JSON structured logging, request ID tracing, full audit log
- **Containerized** — Docker Compose with pgvector + Redis out of the box

## Tech Stack

| Category | Choice |
|---|---|
| **API Framework** | FastAPI (async) |
| **Language** | Python 3.11+ |
| **Vector Store** | pgvector (PostgreSQL extension) |
| **Cache** | Redis 7 |
| **Database** | PostgreSQL 16 |
| **Auth** | JWT (configurable RS256/HS256) |
| **LLM Providers** | OpenAI · Anthropic · Groq |
| **Embeddings** | text-embedding-3-small (pluggable) |
| **Containerization** | Docker + Docker Compose |
| **Observability** | Prometheus · Grafana-ready |
| **CI** | GitHub Actions (lint + type-check + test) |

## Project Structure

```
src/
├── api/                  # FastAPI application
│   ├── main.py           # App entrypoint
│   ├── config.py         # Pydantic settings
│   ├── database.py       # Async SQLAlchemy engine
│   ├── dependencies.py   # Auth + RBAC dependencies
│   ├── models/           # 7 SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response
│   ├── routers/          # auth, query, admin, metrics
│   └── services/         # auth, cache, ingestion, retrieval, generation, hallucination
├── ingestion/            # Extractors, chunker, embedder, pipeline
├── llm/                  # Provider abstraction (OpenAI, Anthropic, Groq)
├── eval/                 # Eval runner + golden dataset
├── common/               # Logger, exceptions, middleware, utils
├── tests/                # Unit + integration tests
├── infra/                # Dockerfile, docker-compose.yml, init.sql
└── alembic/              # Schema migrations (pgvector)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- An LLM API key (OpenAI, Anthropic, or Groq)

### Setup

```bash
# Clone and enter the project
git clone <repo-url> && cd ai-customer-operations

# Copy environment template
cp .env.example .env
# Edit .env — set your LLM_API_KEY and EMBEDDING_API_KEY

# Start infrastructure
docker compose -f src/infra/docker-compose.yml up -d

# Run database migrations
alembic upgrade head

# Verify the API is live
curl http://localhost:8000/health
# → {"status": "ok", "service": "AI Customer Operations Automation"}
```

### API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/health` | Health check | No |
| `POST` | `/auth/login` | Get JWT tokens | No |
| `POST` | `/auth/refresh` | Refresh access token | No |
| `POST` | `/v1/query` | Ask a question (SSE stream) | JWT |
| `POST` | `/v1/admin/documents` | Upload document for ingestion | Admin |
| `GET` | `/v1/admin/dashboard/metrics` | System metrics | Admin |
| `GET` | `/metrics` | Prometheus metrics | No |
| `GET` | `/docs` | OpenAPI documentation | No |

### Example Query

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}' \
  | jq -r '.access_token')

# Ask a question (streaming response)
curl -N -X POST http://localhost:8000/v1/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is your return policy?"}'
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest src/tests/ -v --cov=src

# Lint
ruff check src/

# Type check
mypy src/ --ignore-missing-imports
```

## Deployment

The application is fully containerized and K8s-ready. For production deployment:

1. Set `DEBUG=false` and configure secure `JWT_SECRET_KEY`
2. Use a managed PostgreSQL with pgvector (e.g., Supabase, Neon)
3. Use a managed Redis instance
4. Store secrets in a cloud secret manager (not `.env`)
5. Deploy behind a reverse proxy with TLS termination
6. Configure Prometheus + Grafana for monitoring

## License

MIT

---

Built with Python, FastAPI, pgvector, and Redis.
