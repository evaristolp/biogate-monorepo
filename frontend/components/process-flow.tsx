"use client"

import { useScrollReveal } from "@/hooks/use-scroll-reveal"

// A real-time operational log — not a diagram, not a list.
// The product, visible and working. Nothing else looks like this.

const LOG_LINES = [
  { time: "08:14:22", op: "UPLOAD", label: "vendor_list_q1_2026.csv", detail: "847 entities detected",    color: "text-[#585858]" },
  { time: "08:14:23", op: "NORMALIZE", label: "Resolving names, aliases, subsidiaries", detail: "",    color: "text-[#585858]" },
  { time: "08:14:24", op: "SCREEN · BIS",   label: "Bureau of Industry and Security",    detail: "19,311 entries",  color: "text-[#585858]" },
  { time: "08:14:31", op: "SCREEN · OFAC",  label: "SDN and Blocked Persons List",       detail: "7,892 entries",   color: "text-[#585858]" },
  { time: "08:14:38", op: "SCREEN · DOD",   label: "Section 1260H Covered Entities",     detail: "1,261 entries",   color: "text-[#585858]" },
  { time: "08:14:45", op: "SCREEN · UFLPA", label: "Uyghur Forced Labor Prevention Act", detail: "4,100+ entries",  color: "text-[#585858]" },
] as const

const RESULT_LINES = [
  { time: "08:19:06", op: "COMPLETE",  label: "847 vendors · 4 watchlists · 0 errors", color: "text-[#1E8449]" },
  { time: "08:19:06", op: "FINDINGS",  label: "4 PROHIBITED  ·  2 HIGH RISK  ·  1 REVIEW  ·  840 CLEARED", color: "text-[#D68910]" },
  { time: "08:19:07", op: "DELIVERED", label: "Report transmitted → counsel@organization.com", color: "text-[#C9A96E]" },
] as const

export function ProcessFlow() {
  const headerRef = useScrollReveal<HTMLDivElement>()
  const terminalRef = useScrollReveal<HTMLDivElement>()

  return (
    <section id="how-it-works" className="scroll-mt-20 bg-[#090909] px-6 py-28">
      <div className="mx-auto max-w-[1200px]">

        {/* Header */}
        <div ref={headerRef} className="reveal mb-14">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px w-8 bg-[#C9A96E]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#C9A96E]">
              How it works
            </span>
          </div>
          <h2 className="font-display text-[36px] font-normal leading-tight text-[#F0EEE8] md:text-[44px]">
            From vendor list to intelligence report.
          </h2>
          <p className="mt-3 max-w-lg text-[16px] text-[#909090]">
            One upload. Four federal watchlists. Your answer in under an hour.
          </p>
        </div>

        {/* Terminal window */}
        <div ref={terminalRef} className="reveal">
          <div className="rounded-sm border border-[#1E1F23] bg-[#0D0D0F] overflow-hidden">

            {/* Window chrome */}
            <div className="flex items-center justify-between border-b border-[#1E1F23] px-5 py-3.5">
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-full bg-[#1E1F23]" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#1E1F23]" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#1E1F23]" />
              </div>
              <span className="font-mono text-[10px] tracking-[0.15em] text-[#3A3A3E] uppercase">
                biogate · screening operation · live
              </span>
              <div className="flex items-center gap-2">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#1E8449] animate-pulse" />
                <span className="font-mono text-[10px] text-[#3A3A3E]">ACTIVE</span>
              </div>
            </div>

            {/* Log lines */}
            <div className="p-6 sm:p-8">
              <div className="space-y-1.5">
                {LOG_LINES.map((line) => (
                  <div
                    key={`${line.time}-${line.op}`}
                    className="grid grid-cols-[80px_140px_1fr_auto] items-baseline gap-x-5 sm:grid-cols-[88px_160px_1fr_auto]"
                  >
                    <span className="font-mono text-[11px] text-[#404045] tabular-nums">{line.time}</span>
                    <span className="font-mono text-[11px] tracking-[0.08em] text-[#6B6B70]">{line.op}</span>
                    <span className="font-mono text-[11px] text-[#909090] truncate">{line.label}</span>
                    <span className="font-mono text-[11px] text-[#585858] tabular-nums text-right hidden sm:block">{line.detail}</span>
                  </div>
                ))}
              </div>

              {/* Divider */}
              <div className="my-5 h-px bg-[#1A1B1F]" />

              {/* Result lines */}
              <div className="space-y-1.5">
                {RESULT_LINES.map((line) => (
                  <div
                    key={`${line.time}-${line.op}`}
                    className="grid grid-cols-[80px_140px_1fr] items-baseline gap-x-5 sm:grid-cols-[88px_160px_1fr]"
                  >
                    <span className="font-mono text-[11px] text-[#404045] tabular-nums">{line.time}</span>
                    <span className={`font-mono text-[11px] tracking-[0.08em] font-medium ${line.color}`}>{line.op}</span>
                    <span className={`font-mono text-[11px] ${line.color}`}>{line.label}</span>
                  </div>
                ))}
              </div>

              {/* Cursor */}
              <div className="mt-5 flex items-center gap-2">
                <span className="font-mono text-[11px] text-[#404045]">08:19:07</span>
                <span className="inline-block h-3.5 w-0.5 bg-[#C9A96E]/50 animate-pulse" />
              </div>
            </div>

          </div>

          {/* Caption */}
          <p className="mt-5 text-[12px] text-[#585858] max-w-2xl">
            Every operation timestamped. Every watchlist version logged. Every match cited.
            Reproducible. Defensible. Ready for counsel.
          </p>
        </div>

      </div>
    </section>
  )
}
