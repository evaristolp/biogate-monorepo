"use client"

import Link from "next/link"
import { ArrowRight } from "lucide-react"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"

export function FinalCta() {
  const ref = useScrollReveal<HTMLDivElement>()

  return (
    <section id="contact" className="scroll-mt-20 bg-[#090909] px-6 py-32">
      <div ref={ref} className="reveal mx-auto max-w-[1200px]">

        {/* Deadline note */}
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#585858] mb-6">
          OMB BCC list publication · December 2026
        </p>

        {/* Headline */}
        <h2 className="font-display max-w-2xl text-[44px] font-normal leading-[1.1] text-[#F0EEE8] md:text-[56px]">
          Your vendor list is a liability until it is screened.
        </h2>

        <p className="mt-6 max-w-lg text-[16px] leading-relaxed text-[#909090]">
          The OMB BCC list publishes in December. We deliver the screening
          report before the question gets asked. One upload. Four watchlists.
          Your answer in under an hour.
        </p>

        {/* CTA */}
        <div className="mt-10 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <a
            href="https://calendar.app.google/sFB8cQVniVv2eVAJA"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2.5 rounded-sm bg-[#C9A96E] px-8 py-3.5 text-sm font-medium text-[#090909] transition-all hover:bg-[#D4B87A]"
          >
            Schedule briefing
            <ArrowRight className="h-4 w-4" />
          </a>
          <p className="text-[13px] text-[#585858]">
            Screened against 4 federal watchlists · No legal advice implied
          </p>
        </div>
      </div>
    </section>
  )
}
