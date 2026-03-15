import Link from "next/link"
import { ArrowRight } from "lucide-react"

export function HeroSection() {
  return (
    <section className="w-full px-6 pb-36 pt-32">
      <div className="mx-auto max-w-[1200px]">

        {/* Eyebrow */}
        <div className="mb-8 flex items-center gap-3">
          <div className="h-px w-8 bg-[#C9A96E]" />
          <span className="text-[11px] font-medium uppercase tracking-[0.2em] text-[#C9A96E]">
            BIOSECURE Act · Supply chain intelligence
          </span>
        </div>

        {/* Headline */}
        <h1 className="font-display max-w-[780px] text-[64px] font-normal leading-[1.04] tracking-[-0.02em] text-[#F0EEE8] sm:text-[80px] md:text-[96px]">
          Intelligence before the list drops.
        </h1>

        {/* Subheadline */}
        <p className="mt-8 max-w-[500px] text-[16px] leading-[1.72] text-[#909090]">
          The OMB BCC list publishes December 2026. BioGate screens your vendor
          data against four federal watchlists and delivers the intelligence
          report before your auditors arrive.
        </p>

        {/* CTAs */}
        <div className="mt-10 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
          <Link
            href="#contact"
            className="inline-flex items-center gap-2.5 rounded-sm bg-[#C9A96E] px-7 py-3 text-sm font-medium text-[#090909] transition-all hover:bg-[#D4B87A]"
          >
            Request a briefing
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="#how-it-works"
            className="inline-flex items-center gap-2 py-3 pl-2 text-sm text-[#585858] transition-colors hover:text-[#909090]"
          >
            See how it works
            <ArrowRight className="h-3.5 w-3.5 opacity-40" />
          </Link>
        </div>

      </div>
    </section>
  )
}
