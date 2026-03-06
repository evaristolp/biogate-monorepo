# Consolidate Vercel: One Project (biogate-monorepo)

You have two Vercel projects that should be one:

- **v0-bio-gate-landing-page** — the one currently serving www.biogate.us; **has more UI/code** (full landing, components, etc.) from v0.
- **biogate-monorepo** — deploys from this repo; the **frontend/** here has less (audit flow, API proxy to Railway, but not the full v0 landing).

So you can’t just point Vercel at the monorepo and get the same site: the landing page project has way more in it. You have to **merge that code into the monorepo first**, then use one Vercel project.

Goal: **One project** = **one repo** (biogate-monorepo), **one Next.js app** (the `frontend/` folder with the v0 landing + audit proxy), and **www.biogate.us** pointing at it.

---

## Step 0: Merge the landing page code into the monorepo (GitHub + local)

Do this **before** changing Vercel. You’re moving the “way more shit” from the v0 project into **biogate-monorepo/frontend/** so the monorepo has the full UI.

1. **Find the v0 project’s source**
   - **Vercel** → **v0-bio-gate-landing-page** → **Settings** → **Git**: note the **GitHub repo and branch** (e.g. `evaristolp/v0-bio-gate-landing-page`, `main`).
   - If it’s a separate repo, clone it locally. If it’s the same biogate-monorepo but a different branch, switch to that branch and compare.

2. **Copy the v0 app into the monorepo frontend (without overwriting the proxy)**
   - From the v0 repo (or branch), copy into **biogate-monorepo/frontend/**:
     - All of **app/** (pages, layout, styles) — **except** keep the monorepo’s **app/api/audit/submit/route.ts** (the one that proxies to Railway). So merge pages/layout/components from v0, but do **not** replace `frontend/app/api/audit/submit/route.ts` with the old Supabase-only version.
     - All of **components/** (the v0 components).
     - **public/**, **styles/**, config files (**next.config**, **tailwind**, etc.) as needed.
   - Resolve duplicates: if both have `app/page.tsx` or `app/audit/page.tsx`, keep the v0 version for UI but ensure the audit page still calls **/api/audit/submit** (which in the monorepo proxies to the backend). If the v0 audit page called something else, point it to `/api/audit/submit` and pass `file` + `reportEmail`.
   - **package.json**: merge dependencies from the v0 project into **frontend/package.json** so nothing is missing. Run `pnpm install` or `npm install` in **frontend/** and fix any build errors.

3. **Commit and push to the monorepo**
   - From **biogate-monorepo** root: add and commit the updated **frontend/** changes, push to **main** (or a branch you’ll merge to main). Don’t change Vercel yet.

After Step 0, **biogate-monorepo/frontend** should look and behave like the v0 landing page but use the monorepo’s audit API route (which proxies to Railway and sends email).

---

## Step 1: Note current production (no changes yet)

Do all of this in **Vercel** (not GitHub).

1. In Vercel, open the project **v0-bio-gate-landing-page**.
2. **Vercel** → **Settings** → **Environment Variables**: list every variable (e.g. `NEXT_PUBLIC_SUPABASE_*`, `SUPABASE_MONOREPO_*`, `BIOGATE_API_BASE_URL`). Copy them somewhere safe (e.g. a doc or password manager).
3. **Vercel** → **Settings** → **Domains**: note which domain(s) are assigned (e.g. www.biogate.us, biogate.us).
4. **Vercel** → **Settings** → **Git**: note which GitHub repo and branch are connected (e.g. `some-org/v0-bio-gate-landing-page` and `main`). You’ll use this only to compare with the monorepo later; no changes here.

---

## Step 2: Configure the single project (biogate-monorepo)

Do all of this in **Vercel** (the other project).

1. In **Vercel**, open the project **biogate-monorepo** (not v0-bio-gate-landing-page).
2. **Vercel** → **Settings** → **General**:
   - **Framework Preset**: Next.js.
   - **Root Directory**: set to **`frontend`** (so Vercel builds the Next.js app inside the monorepo). Save.
3. **Vercel** → **Settings** → **Git**:
   - **Production Branch**: `main`.
   - Confirm the connected repo is **evaristolp/biogate-monorepo** (or your fork). If it isn’t, connect the correct GitHub repo here.
4. **Vercel** → **Settings** → **Environment Variables**:
   - Add every variable you copied from v0-bio-gate-landing-page (Step 1).
   - Ensure **BIOGATE_API_BASE_URL** = your Railway API URL (e.g. `https://cozy-benevolence-production-f834.up.railway.app`).
   - Apply to **Production** (and Preview if you use it).
5. **Vercel** → **Settings** → **Domains**:
   - Add **www.biogate.us** and **biogate.us** (or your real domains). Leave the old project’s domains for now so you can switch back if needed.

---

## Step 3: Deploy and verify

1. **Vercel** → project **biogate-monorepo** → **Deployments**: trigger a new deployment from `main` (e.g. “Redeploy” on the latest, or push a small commit to the **GitHub** repo).
2. Wait for the build. If it fails, fix the error (e.g. “Edge Function unsupported module” may need a dependency or config change).
3. When the build succeeds, open the **Vercel deployment URL** (e.g. `biogate-monorepo-xxx.vercel.app`) and check:
   - Homepage loads.
   - Auth (login/sign-up) works.
   - Audit flow: upload file + email → submit → backend is called and (if configured) email is sent.
4. Then open **www.biogate.us** (if it’s already assigned to this project). Confirm the same behavior.

---

## Step 4: Switch production to the single project

1. **Vercel** → project **v0-bio-gate-landing-page** → **Settings** → **Domains**: remove **www.biogate.us** and **biogate.us** (or point them elsewhere). That stops the old project from serving the live domain.
2. **Vercel** → project **biogate-monorepo** → **Settings** → **Domains**: ensure **www.biogate.us** and **biogate.us** are assigned here. Vercel will prompt for DNS if needed; follow the instructions.
3. After DNS propagates, **www.biogate.us** is served only by biogate-monorepo.

---

## Step 5: Clean up (optional)

- You can delete the **v0-bio-gate-landing-page** project in Vercel if you no longer need it, or leave it inactive as a backup.

---

## Monorepo build note

If you don’t set **Root Directory** to **`frontend`**, Vercel will try to build from the repo root and the build will fail (no `package.json` at root for the Next.js app). Always set **Root Directory** = **frontend** for this repo.

---

## Quick reference

| Item | Value |
|------|--------|
| Order | Merge v0 code into monorepo **first** (Step 0), then Vercel (Steps 1–4). |
| Single repo | `biogate-monorepo` |
| Production branch | `main` |
| Root Directory (Vercel) | `frontend` |
| Keep in monorepo | `frontend/app/api/audit/submit/route.ts` (proxy to Railway) — don’t replace with v0’s version. |
| Env vars | Copy from v0 project + `BIOGATE_API_BASE_URL` = Railway URL |
| Domains | www.biogate.us, biogate.us on biogate-monorepo project |
