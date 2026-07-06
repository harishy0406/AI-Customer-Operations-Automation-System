# Demo Frontend

Interactive demo for the AI Customer Operations Automation System. No backend required — runs entirely in the browser with realistic mock data.

## Quick Start

```bash
# Option 1: Just open the file directly
open demo/index.html

# Option 2: Serve with Python
cd demo && python -m http.server 8080
# Then open http://localhost:8080

# Option 3: Serve with Node
cd demo && npx serve .
```

## What You Can Try

| Feature | Description |
|---------|-------------|
| **Dashboard** | Key metrics: query volume, deflection rate, hallucination rate, cache hit rate, latency, cost |
| **Query Console** | Ask questions (e.g., "What is your return policy?"), see retrieved chunks, groundedness scores, and 3-tier routing (auto-send / flagged / withheld) |
| **Documents** | View ingested documents with source types, chunk counts, and content hashes; simulate new uploads |
| **Audit Log** | Activity timeline with all system events |

## Demo Credentials

| Email | Role | Access |
|-------|------|--------|
| `admin@acme.com` | admin | Full access |
| `agent@acme.com` | agent | Query only |
| (any email) | customer | Query only |

## Live API Mode

Click "Switch to Live API" in the top bar to point the frontend at a running backend instance. The API base URL defaults to `http://localhost:8000`.
