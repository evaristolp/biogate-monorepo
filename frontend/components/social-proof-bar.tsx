"use client"

import { useScrollReveal } from "@/hooks/use-scroll-reveal"

const stats = [
  { value: "22,000+", label: "Regulated entities" },
  { value: "4", label: "Federal watchlists" },
  { value: "Daily", label: "Automated refresh" },
  { value: "Dec 2026", label: "OMB deadline" },
]

export function SocialProofBar() {
  const ref = useScrollReveal<HTMLElement>()

  return (
    <section
      ref={ref}
      className="reveal border-y border-[#1E1F23] bg-[#0D0D0F] px-6 py-6"
      aria-label="BioGate by the numbers"
    >
      <div className="mx-auto grid max-w-[1200px] grid-cols-2 gap-6 sm:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="text-center">
            <p className="font-display text-[22px] font-normal text-[#C9A96E]">{s.value}</p>
            <p className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.16em] text-[#333336]">
              {s.label}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
