# EverydayElastic

> **When incidents hit, every second counts. Stop searching. Start fixing.**

## The Problem

IT teams waste critical time during incidents searching through scattered documentation, past tickets, runbooks, and policies. Context-switching between systems slows down response times, and finding the right information becomes a bottleneck when you need it most.

## The Solution

EverydayElastic is an AI copilot for IT operations that delivers instant, grounded answers from thousands of documents. Ask in plain English—"What's the runbook for payment gateway timeouts?" or "Show me Sev-1 incidents from last 24 hours"—and get cited answers in under 3 seconds. When critical incidents are detected, the system automatically suggests posting alerts to your Slack war room with all the context your team needs.

### Built for On-Call Teams, SREs, and IT Ops

**No hallucinations.** All responses are grounded in your actual documents with citations.  
**No context-switching.** Search, answer, and action—all in one interface.  
**No wasted time.** Sub-3-second response time, even across 7,800+ documents.

## 🎯 Key Capabilities

- **Conversational Search**: Ask questions in natural language across incident tickets, runbooks, policies, and documentation
- **Grounded AI Responses**: Gemini-powered answers with citations from retrieved documents—zero hallucinations
- **Hybrid Search**: Combines BM25 keyword search with semantic vector retrieval for best relevance
- **Intelligent Reranking**: Vertex AI reranks results to surface the most relevant information first
- **Actionable Intelligence**: Automatically detects critical incidents and suggests follow-up actions
- **Slack Integration**: Post incident alerts directly to team channels with rich formatting (severity, owner, status)
- **Multi-Domain Knowledge**: Search across structured and unstructured data simultaneously

## 🚀 Quick Demo

**Example Query:**  
*"What's the runbook for payment gateway timeouts?"*

**Response (2.8 seconds):**
- ✅ Retrieves relevant runbooks from knowledge base
- ✅ Provides step-by-step resolution with citations
- ✅ Shows related past incidents
- ✅ Suggests posting to `#sev-1-war-room` if severity is high

**Tech Under the Hood:**
- Elasticsearch hybrid search (BM25 + vectors) across 7,800+ documents
- Vertex AI reranking for precision
- Gemini 2.5 Flash for grounded generation
- Slack Block Kit for rich notifications

## 🏗️ Architecture Overview

### Technology Stack

**Backend**
- FastAPI 0.115.0 - High-performance async Python web framework
- Elasticsearch 8.15.1 - Semantic search with Open Inference API
- Google Cloud Vertex AI - Text generation (Gemini 2.5 Flash Lite) and embeddings
- Slack Web API - Rich message formatting with Block Kit
- OpenTelemetry - Observability and metrics collection
- Prometheus - Metrics exposition

**Frontend**
- Next.js 15.5.5 - React framework with App Router and Server Components
- Tailwind CSS 4 - Utility-first styling
- Lucide Icons - Modern icon library
- React Markdown - Rendered AI responses with syntax highlighting

**Infrastructure**
- Google Cloud Run - Serverless container deployment
- Elasticsearch Cloud - Managed Elasticsearch cluster
- Google Cloud Storage - Document storage and processing

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed architecture diagram and data flow.

## Prerequisites
- Node.js 20+
- Python 3.11+
- npm (for frontend) & pip/uv (for backend)
- gcloud CLI (>= 471.0.0) with an authenticated account and active project
- Elastic Cloud deployment with semantic search enabled
- Google Cloud service account JSON with Vertex AI permissions (set via `GOOGLE_APPLICATION_CREDENTIALS`)

## Environment Variables
Create a `.env` (or export in terminal) for both backend and frontend as needed.

```bash
# .env (root directory)
ELASTIC_ENDPOINT="https://<your-deployment>.es.us-central1.gcp.cloud.es.io"
ELASTIC_USERNAME="elastic"
ELASTIC_PASSWORD="your-password"
VERTEX_PROJECT_ID="your-gcp-project-id"
EMBEDDING_INFERENCE_ID="google_vertex_ai_embeddings"
RERANKER_INFERENCE_ID="google_vertex_ai_rerank"
VERTEX_MODEL="gemini-2.5-flash-lite"
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Observability (optional but recommended)
ENABLE_TRACING=true
OTEL_EXPORTER_ENDPOINT="https://<your-deployment>.apm.us-central1.gcp.cloud.es.io:443/v1/traces"
OTEL_EXPORTER_HEADERS="Authorization=Bearer <elastic-apm-token>"
OTEL_EXPORTER_INSECURE=false

# Slack Integration (optional)
SLACK_ACCESS_TOKEN=xoxe.xoxp-1-...
SLACK_REFRESH_TOKEN=xoxe-1-...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
DEFAULT_SLACK_CHANNEL="sev-1-war-room"
```

Frontend expects the API base URL via `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
```

## 🚀 Get Started in 5 Minutes

### What You Need
- Python 3.11+ and Node.js 20+
- Google Cloud account with Vertex AI API enabled ([free trial available](https://cloud.google.com/free))
- Elasticsearch Cloud deployment ([14-day free trial](https://cloud.elastic.co/registration))
- Slack workspace (optional, for incident notifications)

### Backend Setup (2 minutes)

```bash
# 1. Clone and navigate to project
cd backend

# 2. Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment variables from root .env
cp ../.env .env

# 5. Start development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**✅ Backend Running!** Verify at:
- `http://localhost:8000/health` - Health check
- `http://localhost:8000/integrations/status` - Integration status
- `http://localhost:8000/metrics` - Prometheus metrics

### Frontend Setup (2 minutes)

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Create environment file
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

# 4. Start development server
npm run dev
```

**🎉 You're Live!**  
- **Landing page**: `http://localhost:3000`
- **Chat with AI**: `http://localhost:3000/copilot`

Try asking: *"Show me Sev-1 incidents from the last 24 hours"* or *"What's the runbook for database connection failures?"*

### Quality Checks (Optional)
```bash
cd backend
pytest

cd ../frontend
npm run lint
npm run build
```

## Cloud Run Deployment

### 1. Build and push backend container
Ensure `backend/Dockerfile` exists (see notes below). Then run:
```bash
export PROJECT_ID="<gcp-project>"
export REGION="us-central1"
export SERVICE="everydayelastic-backend"

gcloud builds submit ./backend \
  --tag "gcr.io/${PROJECT_ID}/${SERVICE}:$(git rev-parse --short HEAD)"
```

Deploy to Cloud Run with required environment variables and secrets:
```bash
gcloud run deploy ${SERVICE} \
  --image "gcr.io/${PROJECT_ID}/${SERVICE}:$(git rev-parse --short HEAD)" \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "VERTEX_PROJECT_ID=${PROJECT_ID},VERTEX_LOCATION=us-central1,VERTEX_MODEL=gemini-2.5-flash-lite,EMBEDDING_INFERENCE_ID=google_vertex_ai_embeddings,RERANKER_INFERENCE_ID=google_vertex_ai_rerank" \
  --set-secrets "ELASTIC_ENDPOINT=elastic-endpoint:latest,ELASTIC_USERNAME=elastic-username:latest,ELASTIC_PASSWORD=elastic-password:latest,SLACK_ACCESS_TOKEN=slack-access-token:latest,SLACK_REFRESH_TOKEN=slack-refresh-token:latest,SLACK_CLIENT_ID=slack-client-id:latest,SLACK_CLIENT_SECRET=slack-client-secret:latest,SLACK_WEBHOOK_URL=slack-webhook-url:latest,DEFAULT_SLACK_CHANNEL=default-slack-channel:latest,ENABLE_TRACING=enable-tracing:latest,OTEL_EXPORTER_ENDPOINT=otel-exporter-endpoint:latest,OTEL_EXPORTER_HEADERS=otel-exporter-headers:latest,OTEL_EXPORTER_INSECURE=otel-exporter-insecure:latest" \
  --service-account "vertex-runner@${PROJECT_ID}.iam.gserviceaccount.com"
```
Mount the service-account JSON via Secret Manager or use Workload Identity Federation (recommended) instead of shipping raw keys.

### 2. Build and push frontend container
Example `frontend/Dockerfile` should run a Next.js production build and serve with `next start`:
```bash
export FRONTEND_SERVICE="everydayelastic-frontend"

gcloud builds submit ./frontend \
  --tag "gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE}:$(git rev-parse --short HEAD)"

gcloud run deploy ${FRONTEND_SERVICE} \
  --image "gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE}:$(git rev-parse --short HEAD)" \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "NEXT_PUBLIC_API_BASE_URL=https://<backend-service-url>"
```

### 3. Post-deployment
- Hit `/integrations/status` on the backend URL to validate Elastic and Vertex connectivity.
- Load the frontend Cloud Run URL and confirm `/copilot` can generate responses with cited sources.
- Configure a custom domain or Cloud Load Balancer if a single entrypoint is required.

## Observability & Logging
- Backend logging includes `logger.exception("Vertex AI generation failed")` in `backend/app/api/routes.py` for debugging.
- Enable **Cloud Logging** and **Cloud Trace** on both services for deeper insights.
- Elastic Observability can ingest backend structured logs by forwarding from Cloud Logging.

## 📊 How It Works

### Smart Search Pipeline: Fast & Accurate
Your query goes through multiple layers of intelligence to deliver the best answer:

1. **Query Understanding**: Automatically detects context (incident vs. policy vs. runbook) and applies smart filters
2. **Hybrid Retrieval**: Combines keyword matching (BM25) with semantic understanding (vector search) using Elasticsearch
3. **Relevance Reranking**: Vertex AI reranks results to ensure the most relevant documents surface first
4. **Context Assembly**: Top 4 most relevant documents form the knowledge base for AI generation
5. **Grounded Response**: Gemini 2.5 Flash generates answers with citations—no hallucinations, just facts

**Result**: Sub-3-second end-to-end latency from query to cited answer.

### Incident Management Made Easy
When the AI detects critical incidents (Sev-1, Sev-2), it suggests posting to Slack automatically:

- **Rich Alerts**: Uses Slack Block Kit for structured, scannable incident data
- **All Context Included**: Severity, status, owner, affected service—everything your team needs
- **No Manual Work**: One click from detection to war room notification
- **Reliable Delivery**: Primary OAuth-based Web API with automatic webhook fallback
- **Team Coordination**: Posts to configured channels (e.g., `#sev-1-war-room`)

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Build Verification
```bash
cd frontend
npm run lint
npm run build
```

### Integration Status Check
```bash
curl http://localhost:8000/integrations/status | jq
```

Expected output:
```json
{
  "elastic": {"status": "green", "cluster_name": "..."},
  "vertex_ai": {"status": "enabled", "model": "gemini-2.5-flash-lite"},
  "slack": {"status": "enabled", "method": "web_api", "channel": "sev-1-war-room"}
}
```

## 📁 Project Structure

```
everydayelastic/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py          # Chat and action endpoints
│   │   ├── core/
│   │   │   ├── config.py          # Configuration management
│   │   │   ├── logging_config.py  # Structured logging
│   │   │   └── metrics.py         # Prometheus metrics
│   │   ├── services/
│   │   │   ├── elastic.py         # Elasticsearch client
│   │   │   ├── vertex.py          # Vertex AI client
│   │   │   ├── slack_client.py    # Slack integration
│   │   │   └── workflows.py       # Follow-up suggestions
│   │   ├── schemas/
│   │   │   └── chat.py            # Pydantic models
│   │   └── main.py                # FastAPI application
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Landing page
│   │   │   ├── copilot/
│   │   │   │   └── page.tsx       # Chat interface
│   │   │   └── globals.css        # Global styles
│   │   └── components/
│   ├── Dockerfile
│   └── package.json
├── .env                           # Environment variables
├── ARCHITECTURE.md                # Architecture documentation
└── README.md                      # This file
```

## 🚢 Production Deployment

Ready to deploy? See the **Cloud Run Deployment** section above for step-by-step instructions to get your backend and frontend live on Google Cloud. Complete infrastructure-as-code with secrets management, auto-scaling, and monitoring built in.

## 📝 License

MIT License - see LICENSE file for details.

---

**Built with ❤️ for IT teams who deserve better incident response tools.**

*Stop searching. Start fixing.*
