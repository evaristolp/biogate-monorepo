"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export default function SignUpPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const supabase = createClient()
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo:
          process.env.NEXT_PUBLIC_DEV_SUPABASE_REDIRECT_URL ||
          `${window.location.origin}/auth/callback`,
      },
    })

    console.log("[v0] signUp response data:", JSON.stringify(data, null, 2))
    console.log("[v0] signUp response error:", error)

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    // If user already exists but is unconfirmed, Supabase returns a fake user with empty identities
    if (data?.user?.identities?.length === 0) {
      setError("An account with this email already exists. Please sign in or check your inbox for a confirmation link.")
      setLoading(false)
      return
    }

    router.push("/auth/sign-up-success")
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#0c1222]">
      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full max-w-sm">
          <Link
            href="/"
            className="mb-10 block text-3xl font-extrabold tracking-tight text-white"
          >
            biogate
          </Link>
          <h1 className="text-2xl font-bold text-white">Create your account</h1>
          <p className="mt-2 text-sm text-white/50">
            Get started with your free compliance audit.
          </p>

          <form onSubmit={handleSignUp} className="mt-8 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-white/70">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@biotech.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="border-white/10 bg-white/5 text-white placeholder:text-white/30 focus-visible:ring-blue-500"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-white/70">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="Min 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="border-white/10 bg-white/5 text-white placeholder:text-white/30 focus-visible:ring-blue-500"
              />
            </div>

            {error && (
              <p className="text-sm text-red-400">{error}</p>
            )}

            <Button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-white font-semibold text-foreground hover:bg-white/90"
            >
              {loading ? "Creating account..." : "Create account"}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-white/40">
            Already have an account?{" "}
            <Link href="/auth/login" className="text-white/70 underline hover:text-white">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
