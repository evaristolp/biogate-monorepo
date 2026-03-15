import { createClient as createServerClient } from "@/lib/supabase/server"
import { NextResponse } from "next/server"

function normalizeBaseUrl(raw: string | undefined): string {
  if (!raw?.trim()) return "http://localhost:8000"
  const s = raw.trim()
  if (/^https?:\/\//i.test(s)) return s
  return `https://${s}`
}

const BACKEND_URL = normalizeBaseUrl(
  process.env.BIOGATE_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL
)

/** Extract a readable error message from FastAPI error response (detail can be string, object, or array). */
function normalizeBackendError(data: unknown): string {
  if (data == null || typeof data !== "object") return "Audit failed"
  const d = data as Record<string, unknown>
  const detail = d.detail
  if (typeof detail === "string") return detail || "Audit failed"
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const msg = (detail as Record<string, unknown>).message
    if (typeof msg === "string") return msg
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as Record<string, unknown>
    const msg = first?.msg ?? first?.message
    if (typeof msg === "string") return msg
  }
  const err = d.error
  if (typeof err === "string") return err
  return "Audit failed"
}

export async function POST(request: Request) {
  // Verify the user is authenticated
  const supabaseAuth = await createServerClient()
  const {
    data: { user },
  } = await supabaseAuth.auth.getUser()

  if (!user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 })
  }

  try {
    const formData = await request.formData()
    const reportEmail = formData.get("reportEmail") as string
    const file = formData.get("file") as File

    if (!file) {
      return NextResponse.json({ error: "Missing file" }, { status: 400 })
    }

    // Proxy to BioGate FastAPI backend: runs audit + sends email if reportEmail provided
    const backendForm = new FormData()
    backendForm.set("file", file)
    if (reportEmail?.trim()) {
      backendForm.set("email", reportEmail.trim())
    }

    const headers: Record<string, string> = {}
    const apiKey = process.env.BIOGATE_API_KEY
    if (apiKey) headers["Authorization"] = `Bearer ${apiKey}`

    const res = await fetch(`${BACKEND_URL}/audits/upload_and_audit`, {
      method: "POST",
      body: backendForm,
      headers,
    })

    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      const message = normalizeBackendError(data)
      return NextResponse.json({ error: message }, { status: res.status })
    }

    return NextResponse.json(data)
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Server error" },
      { status: 500 }
    )
  }
}
