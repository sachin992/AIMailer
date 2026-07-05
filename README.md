# AIMailer

Production-focused AI email automation system that combines Gmail ingestion, retrieval-augmented generation, confidence-based decisioning, and human-in-the-loop review.

## GenAI Engineer Profile

I built this project as a GenAI Engineer with emphasis on reliability, observability, and scalable workflow design.

Core experience represented in this project and my stack:

- LangChain for LLM orchestration patterns
- LangGraph for stateful, multi-step agent workflows
- LangSmith for tracing, evaluation, and observability
- FastAPI and Flask for API-oriented AI services
- RAG pipelines using embeddings and vector retrieval
- Human-in-the-loop safety controls for production usage

## What This System Does

- Reads unread emails through Gmail API
- Extracts user intent from incoming content
- Retrieves relevant FAQ context with FAISS search
- Generates grounded responses with OpenAI models
- Auto-sends high-confidence responses
- Routes uncertain responses for admin review
- Stores processing history and metrics in SQLite
- Serves admin operations through API + dashboard

## Tech Stack

- AI/LLM: OpenAI, LangChain, LangGraph
- Observability: LangSmith-ready instrumentation stack
- Backend APIs: Flask (current service), FastAPI-compatible architecture
- Retrieval: FAISS, pandas, numpy
- Security: JWT, bcrypt
- Integrations: Gmail API OAuth2
- Frontend: React, Vite, Nginx
- Deployment: Docker Compose

## Repository Structure

```text
AIMailer/
|-- api_server.py
|-- ai_generator.py
|-- gmail_client.py
|-- faq_manager.py
|-- database.py
|-- auth.py
|-- config.py
|-- bootstrap_admin.py
|-- admin_cli.py
|-- docker-compose.yml
|-- Dockerfile
|-- requirements.txt
|-- faq.xlsx
|-- admin-dashboard/
|   |-- src/
|   |-- Dockerfile
|   `-- nginx.conf
`-- templates/
	`-- email/default.html
```

## Prerequisites

- Python 3.12+
- Docker Desktop
- Gmail OAuth credentials file (`credentials.json`)
- OpenAI API key

## Environment Setup

1. Create environment file:

```bash
copy .env.example .env
```

2. Update mandatory values in `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
GMAIL_CREDENTIALS_FILE=credentials.json
EMAIL_WHITELIST=example1@gmail.com,example2@gmail.com
```

3. Ensure these files exist in project root:

- `credentials.json`
- `faq.xlsx`

## Run With Docker

```bash
docker compose up -d --build
```

Endpoints:

- API: `http://localhost:5000`
- Admin Dashboard: `http://localhost:3000`

Stop:

```bash
docker compose down
```

## Run Locally

```bash
pip install -r requirements.txt
python api_server.py
```

For dashboard development:

```bash
cd admin-dashboard
npm install
npm run dev
```

## Security Checklist Before GitHub Push

- Do not commit `.env`, `token.json`, or `credentials.json`
- Rotate any leaked API keys immediately
- Replace placeholder JWT secrets for non-local environments

## Why This Project Is Portfolio-Ready

- Real-world GenAI workflow with retrieval + generation + review loop
- Practical automation with measurable confidence routing
- Strong production engineering focus (auth, logging, analytics, deployment)
- Clean separation of data, model logic, API layer, and admin UI

## License

Add your preferred license file before publishing (MIT is a common choice).
