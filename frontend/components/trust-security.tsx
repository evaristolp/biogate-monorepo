"use client"

import { Lock, RefreshCw, Database, ShieldCheck, Eye, Server } from "lucide-react"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"

const items = [
  {
    icon: Lock,
    title: "Encrypted end-to-end",
    description: "TLS 1.3 in transit. AES-256 at rest. Your vendor list never travels in the clear.",
  },
  {
    icon: RefreshCw,
    title: "Daily watchlist refresh",
    description: "Federal watchlists ingested and indexed every 24 hours. You screen against the current list, not last month's.",
  },
  {
    icon: Database,
    title: "No training on your data",
    description: "Your vendor data runs your audit. It is never used to train models, shared with other customers, or retained beyond your session.",
  },
  {
    icon: ShieldCheck,
    title: "SOC 2-aligned practices",
    description: "Access controls, audit logging, and change management follow SOC 2 Type II aligned practices.",
  },
  {
    icon: Eye,
    title: "Full audit trail",
    description: "Every screening run is logged with timestamp, watchlist versions, and match evidence. Reproducible and defensible.",
  },
  {
    icon: Server,
    title: "US-only data residency",
    description: "All data stored in US-only regions with database-level account isolation. Built for organizations with federal funding obligations.",
  },
]

export function TrustSecurity() {
  const headerRef = useScrollReveal<HTMLDivElement>()
  const listRef = useScrollReveal<HTMLDivElement>()

  return (
    <section id="security" className="scroll-mt-20 bg-[#0D0D0F] px-6 py-28">
      <div className="mx-auto max-w-[1200px]">

        <div ref={headerRef} className="reveal mb-16">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px w-8 bg-[#C9A96E]" />
            <span className="font-sans text-[11px] font-semibold uppercase tracking-[0.2em] text-[#C9A96E]">
              Security
            </span>
          </div>
          <h2 className="font-display text-[36px] font-normal leading-tight text-[#F0EEE8] md:text-[44px]">
            Built for organizations that answer to regulators.
          </h2>
          <p className="mt-3 max-w-lg text-[16px] text-[#909090]">
            Compliance software operates at a higher standard. Here is exactly
            how we handle your data.
          </p>
        </div>

        {/* Clean 2-column statement list — no cards, no borders on items */}
        <div ref={listRef} className="reveal">
          <div className="grid gap-x-16 md:grid-cols-2">
            {items.map((item, i) => (
              <div
                key={item.title}
                className={`flex items-start gap-5 py-8 ${i < items.length - 2 ? "border-b border-[#1E1F23]" : ""}`}
              >
                <div className="mt-0.5 flex-shrink-0">
                  <item.icon className="h-4 w-4 text-[#C9A96E]" aria-hidden="true" />
                </div>
                <div>
                  <h3 className="mb-1.5 text-[14px] font-medium text-[#F0EEE8]">
                    {item.title}
                  </h3>
                  <p className="text-[13px] leading-relaxed text-[#8A8A90]">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  )
}
