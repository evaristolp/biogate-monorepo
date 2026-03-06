# v0 Prompt: Wire the audit flow to the BioGate FastAPI backend

Copy the prompt below into v0 when you want the Next.js app to run audits and send email reports via the BioGate FastAPI API instead of (or in addition to) any existing Supabase-only flow.

---

## Prompt for v0

**Task:** Wire the audit / vendor screening flow so it calls the BioGate FastAPI backend for the actual audit and email delivery. Keep the current UI (file upload, optional email for report delivery, risk summary, vendor table, certificate download).

**Backend API contract:**

- **Base URL:** Configurable via env. Use `NEXT_PUBLIC_API_BASE_URL` for the backend root (e.g. `https://api.biogate.us` or `http://localhost:8000`). Default to `http://localhost:8000` when unset.
- **Single-file audit:** `POST {baseUrl}/audits/upload_and_audit`
  - **Content-Type:** `multipart/form-data`
  - **Body:** 
    - `file` (required): the uploaded file (CSV or Excel; PDF also supported)
    - `email` (optional): if provided, the backend sends the risk report and Compliance Certificate PDF to this address (requires Resend or SMTP configured on the backend)
  - **Headers:** If the backend is protected with an API key, send `Authorization: Bearer <API_KEY>`. Use a server-side env (e.g. `BIOGATE_API_KEY`) for the key when proxying from a Next.js API route; if the frontend calls the backend directly from the browser, use `NEXT_PUBLIC_BIOGATE_API_KEY` (only if the key is safe to expose).
  - **Response (200):** JSON with `audit_id`, `vendor_count`, `risk_summary` (red/amber/yellow/green counts), `vendors` (array with `id`, `raw_input_name`, `normalized_name`, `country`, `risk_tier`, `effective_score`), `certificate_id`, `certificate_pdf_base64` (base64 PDF), and `ingestion` (extraction metadata).
  - **Errors:** 400 (invalid file, ingestion failed), 401/403 (auth), 429 (rate limit). Parse `detail.message` or `detail` for user-facing error text.

**Implementation options (pick one and implement it):**

1. **Direct client call (simplest):** In the audit upload component, keep calling the FastAPI backend from the browser: `fetch(NEXT_PUBLIC_API_BASE_URL + '/audits/upload_and_audit', { method: 'POST', body: formData, headers: { Authorization: 'Bearer ' + NEXT_PUBLIC_BIOGATE_API_KEY } })`. Ensure the backend has CORS allowed for your frontend origin (e.g. set `CORS_ORIGINS` on the backend to your production domain).

2. **Proxy via Next.js API route (recommended if you don’t want to expose the API key):** Add or update an API route (e.g. `POST /api/audit/run`) that:
   - Accepts `multipart/form-data` with `file` and optional `email`.
   - Forwards the request to `BACKEND_URL/audits/upload_and_audit` (e.g. from `process.env.BIOGATE_API_BASE_URL`), attaching `Authorization: Bearer <BIOGATE_API_KEY>` from server env.
   - Streams back the JSON response and status code to the client.
   The frontend then calls `/api/audit/run` instead of the backend URL; no API key in the browser.

**UI behavior:** Keep the existing audit section: file input, optional email field (“Email report to”), submit button, then show risk summary (red/amber/yellow/green), vendor table, and a “Download certificate PDF” button when `certificate_pdf_base64` is present. Verification link can point to `{baseUrl}/verify/{certificate_id}`.

**Do not** duplicate audit logic in the Next.js app (e.g. inserting into Supabase audits/vendors and never calling FastAPI). The single source of truth for running the audit and sending the email is the FastAPI backend.

---

## Backend checklist (for you)

- Backend has CORS enabled; set `CORS_ORIGINS` to your frontend URL(s), e.g. `https://biogate.us,https://www.biogate.us`.
- Backend is deployed and reachable at the URL you put in `NEXT_PUBLIC_API_BASE_URL` (or `BIOGATE_API_BASE_URL` for the proxy).
- If using API key auth: `BIOGATE_API_KEY` is set on the backend; for proxy option set it (and `BIOGATE_API_BASE_URL`) in the Next.js server env (e.g. Vercel).
- For email delivery: backend has `RESEND_API_KEY` and `BIOGATE_EMAIL_FROM` (or SMTP) configured so that when `email` is sent, the report and PDF are sent.
