# Production-Grade Multi-Agent AI Blog Generation Platform

An enterprise-ready, autonomous multi-agent content generation platform engineered for high reliability, source grounding, and provider independence.

---

## 🌟 Core Architectural Principle

> **Multi-Provider Compatible, Single-Provider Operational**  
> *"Support many, require one, use one."*

The entire system operates with **only ONE configured LLM provider** (OpenAI, Google Gemini, Anthropic Claude, or xAI Grok). No agent depends directly on vendor SDKs. A single centralized `LLMGateway` dispatches all 11 autonomous agents through whichever provider is currently active.

If no provider is configured, the application operates gracefully—allowing users to manage projects, create drafts, and view previous content without crashing.

---

## 🤖 The 11 Autonomous Specialized Agents

```
Topic & Strategy
       ↓
[1] Research Planner       (Deconstructs topic into targeted queries)
       ↓
[2] Researcher             (SSRF-safe external evidence gathering)
       ↓
[3] Source Validator       (Domain credibility scoring & claim extraction)
       ↓
[4] Content Strategist     (Audience alignment & narrative retention hooks)
       ↓
[5] Outline Agent          (Hierarchical H1/H2/H3 architecture & targets)
       ↓
[6] Writer Agent           (Long-form drafting with inline citations)
       ↓
[7] Fact Checker           (Audits draft claims against verified corpus)
       ↓
[8] SEO Agent              (Meta tags, slug, readability & JSON-LD schema)
       ↓
[9] Critic Agent           (Demanding editorial quality scoring 0.0-10.0)
       ↓
[10] Revision Editor       (Conditional polishing loop if score < threshold)
       ↓
[11] Publisher Agent       (Enforces human review gate before CMS syndication)
       ↓
Human Review & CMS Approval
```

---

## 🛡️ Enterprise Security & Governance

- **Argon2id Password Security**: Modern password hashing with secure salting and memory hardness.
- **Granular RBAC**: Three explicit roles: `ADMIN` (internal, full access), `PORTAL_USER` (admin-defined limited access), and `PUBLIC_USER` (public reading and interaction only).
- **Strict Secret Hygiene**: Zero API keys, passwords, or tokens in client bundles, JSON responses, or logs.
- **SSRF Defense**: Strict egress socket filtering blocking loopback (`127.0.0.1`), RFC 1918 private subnets, and cloud metadata endpoints (`169.254.169.254`).
- **Prompt Injection Boundaries**: Untrusted web research content is isolated in `<untrusted_external_content>` tags.
- **Human Review Safeguard**: Default workflow transitions to `IN_REVIEW`; an authorized administrator must approve before an article becomes public.
- **Immutable Audit Logging**: Append-only security audit log recording logins, role changes, and syndication jobs.
- **Budget Control**: Per-article, per-project, and per-user cost ceilings.

---

## 🚀 Quickstart & Local Setup

### 1. Backend (`apps/api`)

```bash
cd apps/api

# Create and activate virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run full automated test suite (18 unit & integration tests)
pytest tests/ -v

# Run FastAPI development server
uvicorn app.main:app --reload --port 8000
```

The interactive API documentation will be available at: `http://localhost:8000/docs`.

### 2. Frontend (`apps/web`)

```bash
cd apps/web

# Install dependencies
npm install

# Build verification
npm run build

# Start Next.js development server
npm run dev
```

The web application will be accessible at: `http://localhost:3000`.

---

## 🐳 Docker setup

For local hot-reload development, copy `.env.example` to `.env`, fill the required local values, then run:

```bash
docker compose up --build -d
```

For the secure EC2/Jenkins deployment, use `docker-compose.yml` together with `docker-compose.prod.yml` and a Jenkins **Secret file** credential. See [`docs/PRODUCTION_DEPLOYMENT.md`](docs/PRODUCTION_DEPLOYMENT.md). Database and Redis are internal-only in production; do not publish their ports.

---

## 🧪 Critical Provider Test Matrix (Tests 1–5)

Run the automated test matrix:

```bash
cd apps/api
.venv/bin/pytest tests/test_llm_gateway_matrix.py -v
```

| Test Scenario | Configured Providers | Active Provider | Result |
|---|---|---|---|
| **Test 1** | OpenAI | OpenAI | ✅ All 11 agents execute with OpenAI |
| **Test 2** | Gemini | Gemini | ✅ All 11 agents execute with Gemini |
| **Test 3** | Claude | Claude | ✅ All 11 agents execute with Claude |
| **Test 4** | OpenAI + Gemini + Claude | Selected: Claude | ✅ Selected provider executes all agents |
| **Test 5** | None | None | ✅ Graceful degradation (`AI_PROVIDER_REQUIRED`), no crash |

---

## 📚 First administrator

No default account or password is committed. Create the initial internal administrator through the protected `/admin-signup` route when no administrator exists, or supply `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` only through the server-side production secret file.
