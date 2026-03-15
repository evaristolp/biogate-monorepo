"use client"

const entries = [
  { name: "BGI Genomics", label: "PROHIBITED", color: "#C0392B" },
  { name: "WuXi AppTec (HK) Ltd.", label: "HIGH RISK", color: "#D68910" },
  { name: "Sangon Biotech Co., Ltd.", label: "PROHIBITED", color: "#C0392B" },
  { name: "Nanjing Vazyme Biotech", label: "REVIEW", color: "#B7950B" },
  { name: "Thermo Fisher Scientific", label: "CLEARED", color: "#1E8449" },
  { name: "New England Biolabs", label: "CLEARED", color: "#1E8449" },
]

export function HeroVisual() {
  return (
    <div
      className="absolute inset-0 overflow-hidden pointer-events-none select-none"
      aria-hidden="true"
    >
      {/* Faint ruled lines — classified document paper feel */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `repeating-linear-gradient(
            to bottom,
            transparent 0px,
            transparent 47px,
            rgba(201, 169, 110, 0.03) 47px,
            rgba(201, 169, 110, 0.03) 48px
          )`,
        }}
      />

      {/* Floating intelligence scan card — desktop only */}
      <div className="absolute right-[5%] top-1/2 -translate-y-[52%] hidden xl:block">
        <div
          className="w-[296px] overflow-hidden border border-[#1E1F23] bg-[#090909]"
          style={{
            boxShadow: "0 32px 80px rgba(0,0,0,0.7), 0 0 0 1px rgba(201,169,110,0.06)",
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[#1E1F23] bg-[#0D0D0F] px-4 py-3">
            <span className="text-[9px] font-medium uppercase tracking-[0.2em] text-[#2E2E32]">
              Screening active
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[#1E8449] animate-pulse" />
              <span className="text-[9px] font-medium text-[#1E8449] tracking-wide">Live</span>
            </span>
          </div>

          {/* Slim progress bar */}
          <div className="relative h-px bg-[#111215]">
            <div className="absolute left-0 top-0 h-full bg-[#C9A96E]/50" style={{ width: "38%" }} />
          </div>

          {/* Entity rows */}
          <div>
            {entries.map((entry, i) => (
              <div
                key={entry.name}
                className={`flex items-center justify-between px-4 py-2.5 ${
                  i < entries.length - 1 ? "border-b border-[#0F0F12]" : ""
                }`}
              >
                <span className="truncate pr-3 text-[10px] text-[#3A3A3E]">
                  {entry.name}
                </span>
                <span
                  className="flex-shrink-0 text-[9px] font-semibold tracking-[0.12em]"
                  style={{ color: entry.color }}
                >
                  {entry.label}
                </span>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="border-t border-[#111215] bg-[#0D0D0F] px-4 py-3">
            <div className="flex items-center justify-between">
              <span className="text-[9px] text-[#2A2A2E]">
                6 of 847 vendors processed
              </span>
              <span className="text-[9px] text-[#2A2A2E] tabular-nums">
                0.7%
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
