"use client"

import { useScrollReveal } from "@/hooks/use-scroll-reveal"

type RiskTier = "green" | "yellow" | "amber" | "red"

interface Vendor {
  name: string
  country: string
  tier: RiskTier
  match: string
}

const vendors: Vendor[] = [
  { name: "Sangon Biotech Co., Ltd.", country: "CN", tier: "red",    match: "BIS Entity List" },
  { name: "BGI Genomics",             country: "CN", tier: "red",    match: "DoD 1260H · UFLPA" },
  { name: "WuXi AppTec (HK) Ltd.",    country: "HK", tier: "amber",  match: "Fuzzy match, DoD 1260H" },
  { name: "Thermo Fisher Scientific", country: "US", tier: "green",  match: "Cleared" },
  { name: "Merck KGaA (Sigma-Aldrich)",country:"DE", tier: "green",  match: "Cleared" },
  { name: "Nanjing Vazyme Biotech",   country: "CN", tier: "yellow", match: "Manual review" },
  { name: "New England Biolabs",      country: "US", tier: "green",  match: "Cleared" },
  { name: "Thermo Electron (Shanghai)",country:"CN", tier: "amber",  match: "Subsidiary risk" },
]

const tierConfig: Record<RiskTier, { label: string; color: string; border: string; dot: string }> = {
  red:    { label: "PROHIBITED", color: "#C0392B", border: "rgba(192,57,43,0.25)",   dot: "#C0392B" },
  amber:  { label: "HIGH RISK",  color: "#D68910", border: "rgba(214,137,16,0.25)",  dot: "#D68910" },
  yellow: { label: "REVIEW",     color: "#B7950B", border: "rgba(183,149,11,0.25)",  dot: "#B7950B" },
  green:  { label: "CLEARED",    color: "#1E8449", border: "rgba(30,132,73,0.25)",   dot: "#1E8449" },
}

const counts = {
  red:    vendors.filter(v => v.tier === "red").length,
  amber:  vendors.filter(v => v.tier === "amber").length,
  yellow: vendors.filter(v => v.tier === "yellow").length,
  green:  vendors.filter(v => v.tier === "green").length,
}

function TierBadge({ tier }: { tier: RiskTier }) {
  const cfg = tierConfig[tier]
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-sm px-2.5 py-1 font-mono text-[10px] font-medium tracking-widest"
      style={{ color: cfg.color, border: `1px solid ${cfg.border}` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: cfg.dot }} />
      {cfg.label}
    </span>
  )
}

export function DashboardMock() {
  const wrapperRef = useScrollReveal<HTMLDivElement>()

  return (
    <section className="bg-[#0D0D0F] px-6 py-28">
      <div className="mx-auto max-w-[1200px]">

        <div className="mb-12">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px w-8 bg-[#C9A96E]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#C9A96E]">
              Screening report
            </span>
          </div>
          <h2 className="font-display text-[36px] font-normal leading-tight text-[#F0EEE8] md:text-[44px]">
            Every vendor. Every risk. Documented.
          </h2>
          <p className="mt-3 max-w-lg text-[16px] text-[#585858]">
            The moment screening completes, you have a structured report with
            match evidence, regulatory citations, and an audit trail.
          </p>
        </div>

        {/* Mock terminal/report */}
        <div
          ref={wrapperRef}
          className="reveal overflow-hidden rounded-sm border border-[#1E1F23] bg-[#090909]"
        >
          {/* Chrome bar */}
          <div className="flex items-center gap-3 border-b border-[#1E1F23] bg-[#111215] px-4 py-3">
            <div className="flex gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-[#1E1F23]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[#1E1F23]" />
              <div className="h-2.5 w-2.5 rounded-full bg-[#1E1F23]" />
            </div>
            <div className="flex-1 rounded-sm bg-[#090909] px-3 py-1 text-center font-mono text-[11px] text-[#333336]">
              biogate.us / report / pre-audit-screening
            </div>
          </div>

          <div className="p-6">
            {/* Report header */}
            <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-widest text-[#333336]">
                  PRE-AUDIT INTELLIGENCE REPORT
                </p>
                <p className="mt-1 text-[14px] font-medium text-[#F0EEE8]">
                  Vendor List · Q1 2026
                </p>
                <p className="mt-0.5 font-mono text-[11px] text-[#585858]">
                  Screened against BIS · OFAC · DoD 1260H · UFLPA
                </p>
              </div>
              <div className="flex gap-3">
                {(["red","amber","yellow","green"] as RiskTier[]).map(tier => (
                  <div key={tier} className="text-center">
                    <p className="text-[22px] font-medium" style={{ color: tierConfig[tier].color }}>
                      {counts[tier]}
                    </p>
                    <p className="font-mono text-[9px] uppercase tracking-wider text-[#333336]">
                      {tierConfig[tier].label}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto border border-[#1E1F23]">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#1E1F23] bg-[#111215]">
                    {["Vendor Name", "Country", "Risk Tier", "Match / Reason"].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-mono text-[9px] uppercase tracking-widest text-[#333336]">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {vendors.map((v, i) => (
                    <tr
                      key={v.name}
                      className={`transition-colors hover:bg-[#111215] ${i < vendors.length - 1 ? "border-b border-[#1A1A1E]" : ""}`}
                    >
                      <td className="px-4 py-3 font-mono text-[12px] text-[#C8C4BC]">{v.name}</td>
                      <td className="px-4 py-3">
                        <span className="rounded-sm border border-[#1E1F23] px-2 py-0.5 font-mono text-[10px] text-[#585858]">
                          {v.country}
                        </span>
                      </td>
                      <td className="px-4 py-3"><TierBadge tier={v.tier} /></td>
                      <td className="px-4 py-3 font-mono text-[11px] text-[#585858]">{v.match}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Footer */}
            <div className="mt-4">
              <p className="font-mono text-[11px] text-[#333336]">
                {vendors.length} vendors screened · Watchlists current as of today
              </p>
            </div>
          </div>
        </div>

        {/* Scope note */}
        <p className="mt-5 text-[12px] text-[#333336]">
          This report is pre-audit analysis, not legal advice. All findings
          require attorney review before any legal determination is made.
        </p>
      </div>
    </section>
  )
}
