\"use client\"

import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export function HeroSection() {
  const handleRunAuditClick = () => {
    if (typeof document === "undefined") return
    const el = document.getElementById("audit")
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  return (
    <section className="bg-primary px-6 pb-28 pt-20">
      <div className="mx-auto max-w-3xl text-center">
        <h1 className="text-balance text-4xl font-bold leading-[1.1] tracking-tight text-primary-foreground sm:text-5xl md:text-6xl">
          Instant BIOSECURE Risk Report for NIH Funded Biotechs
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-pretty text-base leading-relaxed text-primary-foreground/85 md:text-lg">
          Upload your vendor list. Automatically cross-reference against OMB and
          proxy watchlists. Risk Report straight to your email.
        </p>
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <Button
            size="lg"
            className="gap-2 rounded-full bg-primary-foreground px-8 text-sm font-semibold text-primary shadow-none hover:bg-primary-foreground/90"
            onClick={handleRunAuditClick}
          >
            Run free audit
            <ArrowRight className="h-4 w-4" />
          </Button>
          <Button
            size="lg"
            variant="ghost"
            className="rounded-full text-sm font-medium text-primary-foreground/70 hover:bg-primary-foreground/10 hover:text-primary-foreground"
          >
            See how it works
          </Button>
        </div>
      </div>
    </section>
  )
}
