"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { createClient } from "@/lib/supabase/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Upload, FileText, CheckCircle2, ArrowRight, LogOut } from "lucide-react"

type Step = "email" | "upload" | "submitted"

export default function AuditPage() {
  const [step, setStep] = useState<Step>("email")
  const [reportEmail, setReportEmail] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!reportEmail) return
    setStep("upload")
  }

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const onDragLeave = useCallback(() => {
    setDragging(false)
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files?.[0]
    if (dropped) setFile(dropped)
  }, [])

  function onFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0]
    if (selected) setFile(selected)
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("reportEmail", reportEmail)
      formData.append("file", file)

      const res = await fetch("/api/audit/submit", {
        method: "POST",
        body: formData,
      })

      const result = await res.json()

      if (!res.ok) {
        setError(result.error || "Submission failed")
        setUploading(false)
        return
      }

      setStep("submitted")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
    }
  }

  async function handleSignOut() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push("/")
    router.refresh()
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#0c1222]">
      {/* Top bar */}
      <header className="flex items-center justify-between px-8 py-4">
        <Link
          href="/"
          className="text-2xl font-extrabold tracking-tight text-white"
        >
          biogate
        </Link>
        <button
          onClick={handleSignOut}
          className="flex items-center gap-2 text-sm text-white/50 transition-colors hover:text-white/80"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </header>

      {/* Content */}
      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full max-w-md">
          {/* Step 1: Email capture */}
          {step === "email" && (
            <div>
              <h1 className="text-2xl font-bold text-white">
                Run your free audit
              </h1>
              <p className="mt-2 text-sm text-white/50">
                {"Where should we send your risk report?"}
              </p>
              <form onSubmit={handleEmailSubmit} className="mt-8 space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="report-email" className="text-white/70">
                    Report delivery email
                  </Label>
                  <Input
                    id="report-email"
                    type="email"
                    placeholder="compliance@yourcompany.com"
                    value={reportEmail}
                    onChange={(e) => setReportEmail(e.target.value)}
                    required
                    className="border-white/10 bg-white/5 text-white placeholder:text-white/30 focus-visible:ring-blue-500"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full gap-2 rounded-full bg-white font-semibold text-foreground hover:bg-white/90"
                >
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </form>
            </div>
          )}

          {/* Step 2: File upload dropbox */}
          {step === "upload" && (
            <div>
              <h1 className="text-2xl font-bold text-white">
                Upload your vendor list
              </h1>
              <p className="mt-2 text-sm text-white/50">
                {"Drop a CSV, Excel, or PDF with your vendor data. We'll screen it against OMB and proxy watchlists."}
              </p>

              <div
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                className={`mt-8 flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed transition-colors ${
                  dragging
                    ? "border-blue-400 bg-blue-400/10"
                    : file
                      ? "border-green-400/50 bg-green-400/5"
                      : "border-white/15 bg-white/[0.02] hover:border-white/25"
                }`}
                onClick={() =>
                  document.getElementById("file-input")?.click()
                }
                role="button"
                tabIndex={0}
                aria-label="Upload vendor list file"
              >
                <input
                  id="file-input"
                  type="file"
                  accept=".csv,.xlsx,.xls,.pdf,.tsv"
                  onChange={onFileSelect}
                  className="hidden"
                />
                {file ? (
                  <div className="flex flex-col items-center gap-2 px-4 text-center">
                    <FileText className="h-8 w-8 text-green-400" />
                    <p className="text-sm font-medium text-white">
                      {file.name}
                    </p>
                    <p className="text-xs text-white/40">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 px-4 text-center">
                    <Upload className="h-8 w-8 text-white/30" />
                    <p className="text-sm text-white/50">
                      Drag and drop or click to browse
                    </p>
                    <p className="text-xs text-white/30">
                      CSV, Excel, or PDF up to 10 MB
                    </p>
                  </div>
                )}
              </div>

              {error && (
                <p className="mt-3 text-sm text-red-400">{error}</p>
              )}

              <div className="mt-6 flex gap-3">
                <Button
                  variant="ghost"
                  onClick={() => setStep("email")}
                  className="rounded-full text-white/50 hover:bg-white/5 hover:text-white"
                >
                  Back
                </Button>
                <Button
                  onClick={handleUpload}
                  disabled={!file || uploading}
                  className="flex-1 gap-2 rounded-full bg-white font-semibold text-foreground hover:bg-white/90 disabled:opacity-40"
                >
                  {uploading ? "Uploading..." : "Submit for screening"}
                  {!uploading && <ArrowRight className="h-4 w-4" />}
                </Button>
              </div>

              <p className="mt-4 text-center text-xs text-white/30">
                {"Report will be sent to "}
                <span className="text-white/50">{reportEmail}</span>
              </p>
            </div>
          )}

          {/* Step 3: Success */}
          {step === "submitted" && (
            <div className="text-center">
              <CheckCircle2 className="mx-auto h-12 w-12 text-green-400" />
              <h1 className="mt-4 text-2xl font-bold text-white">
                Audit submitted
              </h1>
              <p className="mt-3 text-sm leading-relaxed text-white/50">
                {"We're screening your vendor list now. Your risk report will be delivered to "}
                <span className="text-white/70">{reportEmail}</span>
                {" within a few minutes."}
              </p>
              <Link
                href="/"
                className="mt-8 inline-block text-sm text-white/70 underline hover:text-white"
              >
                Back to home
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
