"use client"

import { useScrollReveal } from "@/hooks/use-scroll-reveal"

const CALENDAR_URL = "https://calendar.app.google/jWgYSizJdFhYJKUU9"

export function FinalCta() {
  const ref = useScrollReveal<HTMLDivElement>()

  return (
    <section id="contact" className="scroll-mt-20 bg-[#F0EEE8] px-6 py-32">
      <div ref={ref} className="reveal mx-auto max-w-[1200px] text-center">
        {/* Headline */}
        <h2 className="font-display text-[36px] font-normal leading-[1.15] text-[#090909] md:text-[48px]">
          Supply chain intelligence for the next generation
        </h2>

        {/* CTA */}
        <div className="mt-10">
          <a
            href={CALENDAR_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-sm bg-[#090909] px-12 py-4 text-[14px] font-medium text-[#F0EEE8] transition-all hover:bg-[#1a1a1a]"
          >
            Schedule Demo
          </a>
        </div>
      </div>
    </section>
  )
}
