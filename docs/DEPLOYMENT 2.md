# Deploying the BioGate API 24/7

This guide covers running the FastAPI backend **always on** (not just local dev) on three low-cost platforms. Your existing services (Supabase, Resend, Anthropic) stay as-is; you only host the API.

---

## Cost summary (always-on, ~24/7)

| Platform   | Typical monthly cost | Notes |
|-----------|----------------------|--------|
| **Fly.io**   | **~$2–6**           | shared-1x 256MB–1GB; best value. |
| **Railway**  | **~$5–15**          | $5 Hobby includes $5 usage; small API often within that. |
| **Render**   | **~$7**             | "Starter" web service, fixed price, always on. |

All support custom domains (e.g. `https://api.biogate.us`). Supabase, Resend, and Anthropic are billed separately by those providers.

---

## Prerequisites

- GitHub repo pushed (e.g. `biogate-monorepo`).
- Env vars ready (see "Environment variables" below). Use your production Supabase, Resend, and optional Anthropic keys.

---

## Option A: Railway (simple, good defaults)

1. **Sign up:** [railway.app](https://railway.app) → Login with GitHub.
2. **New project:** New Project → Deploy from GitHub repo → select `biogate-monorepo`.
3. **Build:**
   - Root directory: `.` (repo root).
   - **Builder:** Dockerfile (use the repo's `Dockerfile`).
   - Start command is already in the Dockerfile: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
4. **Variables:** In the service → Variables, add every env var from your `.env` (see list below). Do **not** commit `.env`; set them in Railway's UI.
5. **Domain:** Settings → Generate Domain (e.g. `biogate-api.up.railway.app`) or add a custom domain and point DNS to Railway.
6. **v0 / frontend:** Set `BIOGATE_API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` to your Railway (or custom) URL, e.g. `https://biogate-api.up.railway.app`. Set `CORS_ORIGINS` on the backend to your frontend origin(s).

**Cost:** Hobby $5/month; a small FastAPI app often stays within the included $5 usage. If it goes over, you pay the difference (e.g. a few dollars more).

---

## Option B: Render (fixed $7/month always-on)

1. **Sign up:** [render.com](https://render.com) → Login with GitHub.
2. **New Web Service:** Connect repo `biogate-monorepo`.
3. **Build & run:**
   - **Environment:** Docker.
   - Render will use the repo's `Dockerfile`; no extra config needed if the Dockerfile is at the repo root.
4. **Environment variables:** Add all vars from the list below in the Render dashboard (Environment tab).
5. **Domain:** Render gives a `*.onrender.com` URL; under Custom Domains you can add `api.biogate.us` (or similar) and follow DNS instructions.
6. **v0 / frontend:** Set `BIOGATE_API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` to the Render URL. Set `CORS_ORIGINS` on the backend to your frontend origin(s).

**Cost:** "Starter" web service is **$7/month** (always on, no spin-down). Free tier spins down after 15 minutes, so it's not "online constantly."

---

## Option C: Fly.io (~$2–6/month)

1. **Install Fly CLI:** `curl -L https://fly.io/install.sh | sh` (or see [fly.io/docs](https://fly.io/docs/hands-on/install-flyctl/)).
2. **Login:** `fly auth login`.
3. **Create app (from repo root):**
   ```bash
   fly launch --no-deploy --name biogate-api
   ```
   When prompted, choose Dockerfile and do not add a Postgres or Redis (you use Supabase).
4. **Scale:** For a small API, 256MB is enough. Edit `fly.toml` or run:
   ```bash
   fly scale memory 256
   ```
5. **Secrets:** Set env vars as Fly secrets (no `.env` in the image):
   ```bash
   fly secrets set SUPABASE_URL="https://YOUR_PROJECT.supabase.co"
   fly secrets set SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
   fly secrets set ANTHROPIC_API_KEY="sk-ant-..."
   fly secrets set RESEND_API_KEY="re_..."
   fly secrets set BIOGATE_EMAIL_FROM="BioGate <noreply@biogate.us>"
   fly secrets set BIOGATE_BASE_URL="https://api.biogate.us"
   fly secrets set CORS_ORIGINS="https://biogate.us,https://www.biogate.us"
   ```
   Add any other vars (e.g. `BIOGATE_API_KEY`, `BIOGATE_CERTIFICATE_PRIVATE_KEY`) the same way.
6. **Deploy:** `fly deploy`.
7. **Domain:** You get `https://biogate-api.fly.dev`. For a custom domain: `fly certs add api.biogate.us` and point DNS as shown.
8. **v0 / frontend:** Set `BIOGATE_API_BASE_URL` and `NEXT_PUBLIC_API_BASE_URL` to the Fly URL (or custom). Ensure `CORS_ORIGINS` on the backend includes your frontend.

**Cost:** shared-1x 256MB is about **~$2/month**; 1GB about **~$6/month**. See [Fly.io pricing](https://fly.io/docs/about/pricing/).

---

## Environment variables (production)

Set these on the platform (Railway / Render / Fly.io); never commit real values.

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL (e.g. `https://xxx.supabase.co`). |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Service role key (not anon). |
| `ANTHROPIC_API_KEY` | No | Claude vendor normalization; omit to skip. |
| `RESEND_API_KEY` | No | For email reports; omit to skip email. |
| `BIOGATE_EMAIL_FROM` | If Resend | e.g. `BioGate <noreply@biogate.us>`. |
| `BIOGATE_BASE_URL` | Recommended | Public API base (e.g. `https://api.biogate.us`) for certificate QR/verify links. |
| `CORS_ORIGINS` | Yes if frontend | Comma-separated origins (e.g. `https://biogate.us,https://www.biogate.us`). |
| `BIOGATE_API_KEY` | No | If set, requests must send `Authorization: Bearer <key>`. |
| `BIOGATE_CERTIFICATE_PRIVATE_KEY` | No | PEM for signing certificates; omit if you don't need verification. |
| `BIOGATE_FREE_CREDITS` | No | Max free audits per identity; omit to disable. |

---

## v0 / Next.js after deploy

In **v0 → Settings → Vars** (or your Next.js host's env):

- **BIOGATE_API_BASE_URL** = your live API URL (e.g. `https://api.biogate.us` or the Railway/Render/Fly URL).
- **NEXT_PUBLIC_API_BASE_URL** = same URL (for client-side links like certificate verification).
- **BIOGATE_API_KEY** = only if you set it on the backend and the frontend sends it (e.g. via proxy).

---

## Build and run the Docker image locally

From the repo root:

```bash
docker build -t biogate-api .
docker run --env-file .env -p 8000:8000 biogate-api
```

Then open `http://localhost:8000/health`. Use the same env vars in production on Railway, Render, or Fly.io.

---

## Quick comparison

- **Cheapest always-on:** Fly.io (~$2–6/month).
- **Easiest setup:** Railway (GitHub → Deploy from repo → add env vars).
- **Predictable price:** Render Starter $7/month.

All three work with the same Dockerfile and env vars; pick one and point your frontend at the deployed API URL.
