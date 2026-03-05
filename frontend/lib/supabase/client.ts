import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_MONOREPO_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_MONOREPO_ANON_KEY!,
  )
}
