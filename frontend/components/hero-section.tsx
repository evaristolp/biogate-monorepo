import Link from "next/link"
import { ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

export function HeroSection() {
  return (
    <section className="w-full px-8 pb-28 pt-20">
      <div className="max-w-3xl text-left">
        <h1 className="text-balance text-4xl font-bold leading-[1.1] tracking-tight text-primary-foreground sm:text-5xl md:text-6xl">
          Instant BIOSECURE Risk Report for NIH Funded Biotechs
        </h1>
        <p className="mt-6 max-w-xl text-pretty text-base leading-relaxed text-primary-foreground/85 md:text-lg">
          Upload your vendor list. Automatically cross-reference against OMB and
          proxy watchlists. Risk Report straight to your email.
        </p>
        <div className="mt-10 flex flex-col items-start gap-3 sm:flex-row">
          <Link href="/audit">
            <Button
              size="lg"
              className="gap-2 rounded-full bg-primary-foreground px-8 text-sm font-semibold text-foreground shadow-none hover:bg-primary-foreground/90"
            >
              Run free audit
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
          <Link href="#how-it-works">
            <Button
              size="lg"
              variant="ghost"
              className="rounded-full text-sm font-medium text-primary-foreground/70 hover:bg-primary-foreground/10 hover:text-primary-foreground"
            >
              See how it works
            </Button>
          </Link>
        </div>
      </div>
    </section>
  )
}
