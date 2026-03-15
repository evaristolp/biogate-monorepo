"use client"

import { X, Check } from "lucide-react"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"

const oldWay = [
  { text: "$50K–$200K per compliance audit" },
  { text: "4–8 weeks from engagement to report" },
  { text: "Manual review — opaque, error-prone" },
  { text: "One-time snapshot that expires immediately" },
  { text: "No audit trail — law firm just hands you a PDF" },
  { text: "You explain your vendor list to someone who doesn't know your lab" },
]

const newWay = [
  { text: "Transparent, fraction of the cost" },
  { text: "Hours — not weeks" },
  { text: "AI-normalized matching with evidence attached" },
  { text: "Daily watchlist refresh — always current" },
  { text: "Full audit trail, every match documented" },
  { text: "Built by someone who has worked in a wet lab" },
]

export function PainPoint() {
  const ref = useScrollReveal<HTMLDivElement>()

  return (
    <section className="bg-[#0B0D17] px-6 py-24">
      <div className="mx-auto max-w-[1200px]">
        {/* Header */}
        <div className="mb-14 text-center">
          <p className="font-mono text-xs font-semibold uppercase tracking-[0.2em] text-[#6B7294]">
            The old way vs. the right way
          </p>
          <h2 className="font-display mt-3 text-3xl font-bold tracking-tight text-[#E8E8E8] md:text-4xl">
            Stop paying law firms to do what software should
          </h2>
        </div>

        {/* Two-column comparison */}
        <div ref={ref} className="reveal grid gap-5 md:grid-cols-2">
          {/* Left — old way */}
          <div className="rounded-2xl border border-[#F0A500]/20 bg-[#1A1F36] p-8">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#F0A500]/10">
                <X className="h-5 w-5 text-[#F0A500]" />
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-[#F0A500]">
                  The law firm way
                </p>
                <p className="font-display text-base font-semibold text-[#E8E8E8]">
                  Manual compliance audits
                </p>
              </div>
            </div>
            <ul className="space-y-4">
              {oldWay.map((item) => (
                <li key={item.text} className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#F0A500]/10">
                    <X className="h-3 w-3 text-[#F0A500]" />
                  </div>
                  <span className="text-sm leading-snug text-[#6B7294]">{item.text}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Right — BioGate */}
          <div className="rounded-2xl border border-[#00D4AA]/25 bg-[#1A1F36] p-8 shadow-[0_0_40px_rgba(0,212,170,0.06)]">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#00D4AA]/10">
                <Check className="h-5 w-5 text-[#00D4AA]" />
              </div>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-[#00D4AA]">
                  The BioGate way
                </p>
                <p className="font-display text-base font-semibold text-[#E8E8E8]">
                  Automated compliance platform
                </p>
              </div>
            </div>
            <ul className="space-y-4">
              {newWay.map((item) => (
                <li key={item.text} className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#00D4AA]/10">
                    <Check className="h-3 w-3 text-[#00D4AA]" />
                  </div>
                  <span className="text-sm leading-snug text-[#E8E8E8]">{item.text}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Quantified summary */}
        <div className="mt-10 grid grid-cols-3 gap-4 rounded-2xl border border-[#2A2D3A] bg-[#1A1F36] p-6 text-center">
          <div>
            <p className="font-display text-2xl font-bold text-[#00D4AA] sm:text-3xl">
              ~$150K
            </p>
            <p className="mt-1 text-xs text-[#6B7294]">avg. law firm audit cost</p>
          </div>
          <div className="border-x border-[#2A2D3A]">
            <p className="font-display text-2xl font-bold text-[#00D4AA] sm:text-3xl">
              6 weeks
            </p>
            <p className="mt-1 text-xs text-[#6B7294]">avg. law firm turnaround</p>
          </div>
          <div>
            <p className="font-display text-2xl font-bold text-[#00D4AA] sm:text-3xl">
              &lt; 1 hr
            </p>
            <p className="mt-1 text-xs text-[#6B7294]">BioGate turnaround</p>
          </div>
        </div>
      </div>
    </section>
  )
}
