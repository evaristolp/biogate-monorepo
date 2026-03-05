"use client"

import * as React from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

type RiskSummary = {
  red: number
  amber: number
  yellow: number
  green: number
}

type TierKey = keyof RiskSummary

type VendorRow = {
  id: string
  raw_input_name: string
  normalized_name?: string | null
  country?: string | null
  risk_tier?: string | null
  effective_score?: number | null
}

type AuditResponse = {
  audit_id: string
  vendor_count: number
  risk_summary?: RiskSummary
  vendors: VendorRow[]
  certificate_id?: string | null
  certificate_pdf_base64?: string | null
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

function buildAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {}
  const apiKey = process.env.NEXT_PUBLIC_BIOGATE_API_KEY
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`
  }
  return headers
}

async function runFullAudit(file: File, email?: string | null): Promise<AuditResponse> {
  const formData = new FormData()
  formData.append("file", file)
  if (email && email.trim()) {
    formData.append("email", email.trim())
  }

  const res = await fetch(`${API_BASE_URL}/audits/upload_and_audit`, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: formData,
  })

  if (!res.ok) {
    let message = "Audit failed. Please try again."
    try {
      const body = (await res.json()) as any
      if (body?.detail?.message) {
        message = body.detail.message as string
      } else if (typeof body?.detail === "string") {
        message = body.detail
      }
    } catch {
      // ignore JSON parsing errors and fall back to default message
    }
    throw new Error(message)
  }

  return (await res.json()) as AuditResponse
}

function getTierBadgeClasses(tier: string | null | undefined): string {
  const base =
    "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize"
  switch (tier) {
    case "red":
      return cn(base, "border-red-200 bg-red-50 text-red-700")
    case "amber":
      return cn(base, "border-amber-200 bg-amber-50 text-amber-700")
    case "yellow":
      return cn(base, "border-yellow-200 bg-yellow-50 text-yellow-700")
    case "green":
      return cn(base, "border-emerald-200 bg-emerald-50 text-emerald-700")
    default:
      return cn(base, "border-muted bg-muted/40 text-muted-foreground")
  }
}

export function AuditUploader() {
  const [file, setFile] = React.useState<File | null>(null)
  const [email, setEmail] = React.useState<string>("")
  const [isSubmitting, setIsSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [result, setResult] = React.useState<AuditResponse | null>(null)

  const summary: RiskSummary = result?.risk_summary ?? {
    red: 0,
    amber: 0,
    yellow: 0,
    green: 0,
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file) return

    setIsSubmitting(true)
    setError(null)

    try {
      const data = await runFullAudit(file, email || undefined)
      setResult(data)
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong."
      setError(message)
      setResult(null)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDownloadCertificate = () => {
    if (!result?.certificate_pdf_base64) return
    try {
      const link = document.createElement("a")
      link.href = `data:application/pdf;base64,${result.certificate_pdf_base64}`
      link.download = `biogate-certificate-${result.certificate_id || "audit"}.pdf`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch {
      // Best-effort; if download fails, we quietly ignore for now.
    }
  }

  const tiers: { key: TierKey; label: string; description: string }[] = [
    {
      key: "red",
      label: "Red",
      description: "High-risk, confirmed watchlist hit",
    },
    {
      key: "amber",
      label: "Amber",
      description: "Probable match, needs review",
    },
    {
      key: "yellow",
      label: "Yellow",
      description: "Low-confidence signal",
    },
    {
      key: "green",
      label: "Green",
      description: "No material watchlist signal",
    },
  ]

  return (
    <section id="audit" className="bg-background px-6 py-16">
      <div className="mx-auto flex max-w-5xl flex-col gap-8">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Run a free BIOSECURE audit
            </CardTitle>
            <CardDescription>
              Upload a CSV or Excel vendor list. We&apos;ll screen it against
              BIS, OFAC, UFLPA, and BIOSECURE-derived entities and show a
              summarized risk report.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={handleSubmit}
              className="flex flex-col gap-4 sm:flex-row sm:items-center"
            >
              <Input
                type="file"
                accept=".csv,.xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(event) => {
                  const nextFile = event.target.files?.[0] ?? null
                  setFile(nextFile)
                  setError(null)
                }}
                aria-label="Upload vendor list file"
              />
              <Input
                type="email"
                placeholder="Email report to (optional)"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-label="Email address for report delivery"
                className="max-w-xs"
              />
              <Button
                type="submit"
                size="lg"
                disabled={!file || isSubmitting}
                className="sm:w-auto"
              >
                {isSubmitting ? (
                  <>
                    <Spinner className="mr-2" />
                    Running audit…
                  </>
                ) : (
                  "Generate risk report"
                )}
              </Button>
            </form>
            {error && (
              <p className="mt-4 text-sm text-destructive" role="alert">
                {error}
              </p>
            )}
            {!error && !result && (
              <p className="mt-4 text-sm text-muted-foreground">
                Files should include a vendor name column (e.g.{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-xs">
                  vendor_name
                </code>{" "}
                or{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-xs">
                  supplier
                </code>
                ) plus optional{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-xs">
                  country
                </code>{" "}
                and{" "}
                <code className="rounded bg-muted px-1 py-0.5 text-xs">
                  parent_company
                </code>
                .
              </p>
            )}
          </CardContent>
        </Card>

        {result && (
          <div className="space-y-8">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-baseline sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
                  Audit complete
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {result.vendor_count} vendors screened for BIOSECURE and
                  related sanctions risk.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                <span className="font-mono text-[11px]">
                  Audit ID: {result.audit_id}
                </span>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-4">
              {tiers.map((tier) => (
                <div
                  key={tier.key}
                  className="rounded-lg border bg-card px-4 py-3"
                >
                  <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                    {tier.label} vendors
                  </p>
                  <p
                    className={cn(
                      "mt-1 text-2xl font-semibold",
                      tier.key === "red" && "text-red-600",
                      tier.key === "amber" && "text-amber-600",
                      tier.key === "yellow" && "text-yellow-600",
                      tier.key === "green" && "text-emerald-600",
                    )}
                  >
                    {summary[tier.key]}
                  </p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {tier.description}
                  </p>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-foreground">
                Vendor-level findings
              </p>
              <div className="rounded-xl border bg-card p-2">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Vendor</TableHead>
                      <TableHead>Normalized name</TableHead>
                      <TableHead>Country</TableHead>
                      <TableHead>Tier</TableHead>
                      <TableHead>Score</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.vendors.map((vendor) => (
                      <TableRow key={vendor.id}>
                        <TableCell className="max-w-xs truncate">
                          {vendor.raw_input_name}
                        </TableCell>
                        <TableCell className="max-w-xs truncate">
                          {vendor.normalized_name || "—"}
                        </TableCell>
                        <TableCell>{vendor.country || "—"}</TableCell>
                        <TableCell>
                          <span className={getTierBadgeClasses(vendor.risk_tier)}>
                            {vendor.risk_tier || "unknown"}
                          </span>
                        </TableCell>
                        <TableCell>
                          {vendor.effective_score != null
                            ? Math.round(vendor.effective_score)
                            : "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>

            {(result.certificate_id || result.certificate_pdf_base64) && (
              <div className="flex flex-col gap-3 rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-foreground">
                    Compliance certificate ready
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Attach the signed PDF to grant paperwork, or verify it
                    via the public endpoint.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {result.certificate_id && (
                    <Button
                      variant="outline"
                      size="sm"
                      asChild
                    >
                      <a
                        href={`${API_BASE_URL}/verify/${result.certificate_id}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open verification JSON
                      </a>
                    </Button>
                  )}
                  {result.certificate_pdf_base64 && (
                    <Button size="sm" onClick={handleDownloadCertificate}>
                      Download certificate PDF
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}

