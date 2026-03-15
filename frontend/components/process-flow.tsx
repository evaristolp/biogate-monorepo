"use client"

import { useEffect, useState, useRef } from "react"
import { useScrollReveal } from "@/hooks/use-scroll-reveal"

type RiskTier = "prohibited" | "high-risk" | "review" | "cleared"

interface VendorNode {
  id: number
  step: number   // 0–4 in pipeline, 5 = sorted
  result: RiskTier
  lane: number   // 0–2 vertical lane
}

const STEPS = [
  {
    label: "UPLOAD",
    count: "847 entities",
    desc: "CSV ingested. Names normalized, aliases resolved, subsidiaries flagged.",
  },
  {
    label: "BIS",
    count: "19,311 entries",
    desc: "Bureau of Industry & Security Entity List. Export controls & foreign policy restrictions.",
  },
  {
    label: "OFAC",
    count: "7,892 entries",
    desc: "SDN and Blocked Persons List. Treasury sanctions and designated nationals.",
  },
  {
    label: "DOD 1260H",
    count: "1,261 entries",
    desc: "Section 1260H Covered Entities. DoD list of Chinese military-affiliated companies.",
  },
  {
    label: "UFLPA",
    count: "4,100+ entries",
    desc: "Uyghur Forced Labor Prevention Act. Companies linked to Xinjiang supply chains.",
  },
]

// horizontal positions (%) along the pipeline track for each step
const STEP_PCT = [6, 25, 46, 67, 88]

// vertical lanes — keeps dots from stacking
const LANE_TOP = ["22%", "50%", "76%"]

const TIERS: { key: RiskTier; label: string; color: string }[] = [
  { key: "prohibited", label: "PROHIBITED", color: "#C0392B" },
  { key: "high-risk",  label: "HIGH RISK",  color: "#D68910" },
  { key: "review",     label: "REVIEW",     color: "#B7950B" },
  { key: "cleared",    label: "CLEARED",    color: "#1E8449" },
]

let uid = 0

function pickTier(): RiskTier {
  const r = Math.random()
  if (r < 0.05) return "prohibited"
  if (r < 0.13) return "high-risk"
  if (r < 0.18) return "review"
  return "cleared"
}

export function ProcessFlow() {
  const headerRef = useScrollReveal<HTMLDivElement>()
  const containerRef = useRef<HTMLDivElement>(null)

  const [nodes, setNodes] = useState<VendorNode[]>([])
  const [counts, setCounts] = useState<Record<RiskTier, number>>({
    prohibited: 0,
    "high-risk": 0,
    review: 0,
    cleared: 0,
  })
  const [active, setActive] = useState(false)

  // Start / stop when section enters view
  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => setActive(e.isIntersecting),
      { threshold: 0.2 }
    )
    if (containerRef.current) obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [])

  useEffect(() => {
    if (!active) return

    const timer = setInterval(() => {
      setNodes(prev => {
        // Advance every node by 1 step
        const advanced = prev.map(n => ({ ...n, step: n.step + 1 }))

        // Nodes completing the pipeline (step just became 5) → increment buckets
        const done = advanced.filter(n => n.step === 5)
        if (done.length > 0) {
          setCounts(c => {
            const u = { ...c }
            done.forEach(n => { u[n.result]++ })
            return u
          })
        }

        // Remove fully expired nodes
        const alive = advanced.filter(n => n.step <= 6)

        // Spawn new node if not too crowded
        const inFlight = alive.filter(n => n.step < 5).length
        if (inFlight < 7 && Math.random() > 0.3) {
          alive.push({
            id: ++uid,
            step: 0,
            result: pickTier(),
            lane: Math.floor(Math.random() * 3),
          })
        }

        return alive
      })
    }, 680)

    return () => clearInterval(timer)
  }, [active])

  return (
    <section id="how-it-works" className="scroll-mt-20 bg-[#090909] px-6 py-28">
      <div className="mx-auto max-w-[1200px]">

        {/* Header */}
        <div ref={headerRef} className="reveal mb-14">
          <div className="mb-4 flex items-center gap-3">
            <div className="h-px w-8 bg-[#C9A96E]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#C9A96E]">
              How it works
            </span>
          </div>
          <h2 className="font-display text-[36px] font-normal leading-tight text-[#F0EEE8] md:text-[44px]">
            From vendor list to screening report.
          </h2>
          <p className="mt-3 max-w-lg text-[16px] text-[#909090]">
            One upload. Four federal watchlists. Your answer in under an hour.
          </p>
        </div>

        {/* Pipeline card */}
        <div ref={containerRef} className="overflow-hidden rounded-sm border border-[#1E1F23] bg-[#0D0D0F]">

          {/* Step info grid */}
          <div className="grid border-b border-[#1E1F23]" style={{ gridTemplateColumns: "repeat(5, 1fr)" }}>
            {STEPS.map((step, i) => (
              <div
                key={step.label}
                className={`px-4 py-5 ${i < 4 ? "border-r border-[#1E1F23]" : ""}`}
              >
                <p className="font-mono text-[10px] font-medium uppercase tracking-[0.16em] text-[#C9A96E]">
                  {step.label}
                </p>
                <p className="mt-0.5 font-mono text-[9px] text-[#333336]">
                  {step.count}
                </p>
                <p className="mt-2 hidden text-[11px] leading-snug text-[#505055] md:block">
                  {step.desc}
                </p>
              </div>
            ))}
          </div>

          {/* Animation track */}
          <div className="relative h-[72px] overflow-hidden border-b border-[#1E1F23] bg-[#090909]">
            {/* Base rail */}
            <div className="absolute top-1/2 left-0 right-0 h-px -translate-y-1/2 bg-[#1A1B1F]" />

            {/* Step gate markers */}
            {STEP_PCT.map((pct, i) => {
              const lit = nodes.some(n => n.step === i)
              return (
                <div
                  key={i}
                  className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${pct}%` }}
                >
                  <div
                    className="h-2.5 w-2.5 rounded-full border-2 transition-all duration-300"
                    style={{
                      borderColor: lit ? "#C9A96E" : "#1E1F23",
                      backgroundColor: lit ? "rgba(201,169,110,0.15)" : "#090909",
                      boxShadow: lit ? "0 0 10px rgba(201,169,110,0.4)" : "none",
                    }}
                  />
                </div>
              )
            })}

            {/* Flowing vendor nodes */}
            {nodes
              .filter(n => n.step >= 0 && n.step < 5)
              .map(node => (
                <div
                  key={node.id}
                  className="absolute -translate-x-1/2 -translate-y-1/2"
                  style={{
                    left: `${STEP_PCT[node.step]}%`,
                    top: LANE_TOP[node.lane],
                    transition: "left 0.65s ease-in-out, opacity 0.3s",
                    opacity: node.step === 4 ? 0.4 : 0.85,
                  }}
                >
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{
                      backgroundColor: "#C9A96E",
                      boxShadow: "0 0 5px rgba(201,169,110,0.6)",
                    }}
                  />
                </div>
              ))}
          </div>

          {/* Result buckets */}
          <div className="grid grid-cols-4">
            {TIERS.map((tier, i) => (
              <div
                key={tier.key}
                className={`px-5 py-6 ${i < 3 ? "border-r border-[#1E1F23]" : ""}`}
              >
                <p
                  className="font-mono text-[9px] uppercase tracking-[0.2em]"
                  style={{ color: tier.color }}
                >
                  {tier.label}
                </p>
                <p className="mt-2 font-mono text-[36px] font-normal leading-none tabular-nums text-[#F0EEE8]">
                  {counts[tier.key]}
                </p>
                {/* Accumulated dots */}
                <div className="mt-3 flex min-h-[10px] flex-wrap gap-1">
                  {Array.from({ length: Math.min(counts[tier.key], 18) }).map((_, j) => (
                    <div
                      key={j}
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ backgroundColor: tier.color, opacity: 0.6 }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>

        </div>

        <p className="mt-5 max-w-2xl text-[12px] text-[#3A3A3E]">
          Every operation timestamped. Every watchlist version logged. Every match cited.
          Reproducible. Defensible. Ready for counsel.
        </p>

      </div>
    </section>
  )
}
