# Production deployment inputs

This project deploys through Jenkins using a **Secret file** credential. The populated runtime file is never committed, returned by the API, baked into the frontend image, or printed by Jenkins.

## Values you must provide

1. **Database and Redis secrets**: create three independent values on the EC2 host:

   ```bash
   openssl rand -hex 32
   ```

   Use one output each for `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, and `SECRET_KEY`. Hex values are URL-safe, so use them unchanged when constructing connection URLs:

   ```text
   DATABASE_URL=postgresql+asyncpg://blogpilot:POSTGRES_PASSWORD@postgres:5432/blogpilot
   REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0
   ```

2. **Bootstrap administrator**: choose an email you control and generate a strong temporary password. Put them in `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD`. Do not set `RESET_INITIAL_ADMIN_PASSWORD=true` unless intentionally resetting that account.

3. **One LLM provider**: create an API key in the provider dashboard you choose, then set only its matching key plus `ACTIVE_PROVIDER` and `ACTIVE_MODEL`:

   - OpenAI: `OPENAI_API_KEY`, `ACTIVE_PROVIDER=openai`
   - Google Gemini: `GEMINI_API_KEY`, `ACTIVE_PROVIDER=gemini`
   - Anthropic: `ANTHROPIC_API_KEY`, `ACTIVE_PROVIDER=anthropic`
   - xAI: `XAI_API_KEY`, `ACTIVE_PROVIDER=xai`

   Use a model identifier that your own provider account has access to. The app validates it through its health check; model names are not hard-coded.

4. **SMTP (optional)**: required only if admins must email invitations. Obtain SMTP hostname, port, username, password/app password, and sender address from your email provider. Leave all SMTP fields blank to disable email delivery safely.

## Create the Jenkins credential

1. On your own machine or EC2, copy `deploy/production.env.example` to a file outside the Git repository, for example `/tmp/blogpilot-production.env`.
2. Fill its blank values. Never paste that populated file into GitHub, an issue, chat, or the repository.
3. In Jenkins, open **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**.
4. Select **Secret file**, upload the populated file, set ID exactly to `blogpilot-production-env`, and save.
5. Securely delete the temporary local file after upload.

## First deployment prerequisites

- DuckDNS must point `blogpilot.duckdns.org` to the EC2 Elastic IP.
- EC2 security group permits inbound TCP `80` and `443`; port `8080`, PostgreSQL, Redis, and the API are not public.
- Caddy is installed. Add the site block in `deploy/Caddyfile.production.example` to `/etc/caddy/Caddyfile`, then validate and reload Caddy:

  ```bash
  sudo caddy validate --config /etc/caddy/Caddyfile
  sudo systemctl reload caddy
  ```

- The Jenkins job is configured as **Pipeline script from SCM** and tracks the protected `main` branch. The job uses the read-only GitHub deploy key already created for Jenkins.

## Deploy and verify

Push a reviewed commit to `main`, then run the Jenkins job. The pipeline tests the API, builds the web application, deploys the Docker stack, and checks `http://127.0.0.1:8000/health`. Caddy exposes the public site at `https://blogpilot.duckdns.org` and routes only `/api/*` to FastAPI.

## Persistent data

PostgreSQL and Redis run on the same EC2 instance through named Docker volumes. They are needed whenever the application is running: PostgreSQL stores users, articles, sources, audit data, and pgvector embeddings; Redis supports rate limiting and future background-job/real-time coordination. Neither is exposed to the internet in production.
