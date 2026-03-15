# Supabase Auth: Email confirmation and rate limits

Sign-up uses Supabase Auth. Confirmation emails are sent by Supabase when **Confirm email** is enabled. If users see "email rate limit exceeded" or never receive the confirmation email, configure the following.

## 1. Enable email confirmation

1. In [Supabase Dashboard](https://supabase.com/dashboard) → your project → **Authentication** → **Providers** → **Email**.
2. Turn **ON** "Confirm email".
3. Set **Redirect URL** (or leave default) so the confirmation link goes to your app, e.g. `https://biogate.us/auth/callback` (the app already uses `emailRedirectTo: origin + '/auth/callback'`).

## 2. Use custom SMTP (recommended for production)

Supabase’s built-in email has a **very low rate limit** (on the order of a few emails per hour). That causes "email rate limit exceeded" and can prevent confirmation emails from being sent.

**Fix:** Use a custom SMTP provider so Supabase sends auth emails (confirmations, magic links, etc.) through your provider.

### Configure custom SMTP (e.g. Resend)

1. **Authentication** → **SMTP Settings** (or **Project Settings** → **Auth** → **SMTP**).
2. Enable **Custom SMTP** and fill in your provider’s details.

**Resend example:**

- **Host:** `smtp.resend.com`
- **Port:** `465` (SSL) or `587` (TLS)
- **User:** `resend`
- **Password:** your Resend API key (e.g. `re_...`)

Use the "From" address you’ve verified in Resend (e.g. `noreply@yourdomain.com` or `BioGate <noreply@biogate.us>`).

### After custom SMTP is set

- Auth emails (including sign-up confirmation) are sent via your SMTP; limits depend on your provider, not Supabase’s built-in cap.
- You can optionally adjust **Authentication** → **Rate Limits** in the Supabase dashboard if you want different caps (e.g. higher for sign-up emails).

## 3. Redirect URL for confirmation links

The frontend already sets:

- `emailRedirectTo: window.location.origin + '/auth/callback'`

So confirmation links will land on `https://your-domain.com/auth/callback?code=...`. The app’s `/auth/callback` route exchanges the code for a session and redirects to `/audit` (or `next`). No code change needed if your site URL is correct in Supabase (**Authentication** → **URL Configuration** → **Site URL**).

## Summary

| Issue | Action |
|-------|--------|
| "email rate limit exceeded" | Enable **Custom SMTP** (e.g. Resend) in Supabase Auth and optionally raise rate limits. |
| Confirmation email not sent | Enable **Confirm email** under Email provider and ensure **Custom SMTP** is configured so emails are actually sent. |
| Wrong redirect after confirm | Set **Site URL** and **Redirect URLs** in Auth URL configuration; app uses `/auth/callback`. |
