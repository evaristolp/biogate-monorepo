"use client"

// A continuous scrolling feed of entities being screened — the most visceral
// proof of what BioGate does. Runs at a pace dignified enough to read.

const ENTRIES = [
  { name: "BGI Genomics",               tier: "PROHIBITED", color: "#C0392B" },
  { name: "Thermo Fisher Scientific",   tier: "CLEARED",    color: "#1E8449" },
  { name: "WuXi AppTec (HK) Ltd.",      tier: "HIGH RISK",  color: "#D68910" },
  { name: "New England Biolabs",        tier: "CLEARED",    color: "#1E8449" },
  { name: "MGI Tech Co., Ltd.",         tier: "PROHIBITED", color: "#C0392B" },
  { name: "Illumina, Inc.",             tier: "CLEARED",    color: "#1E8449" },
  { name: "Nanjing Vazyme Biotech",     tier: "REVIEW",     color: "#B7950B" },
  { name: "PerkinElmer",                tier: "CLEARED",    color: "#1E8449" },
  { name: "Complete Genomics",          tier: "PROHIBITED", color: "#C0392B" },
  { name: "Agilent Technologies",       tier: "CLEARED",    color: "#1E8449" },
  { name: "CellPath Diagnostics Ltd.",  tier: "REVIEW",     color: "#B7950B" },
  { name: "Roche Diagnostics",          tier: "CLEARED",    color: "#1E8449" },
  { name: "SynBio Partners (Shanghai)", tier: "HIGH RISK",  color: "#D68910" },
  { name: "Merck KGaA",                 tier: "CLEARED",    color: "#1E8449" },
  { name: "GenoCore Holdings",          tier: "PROHIBITED", color: "#C0392B" },
  { name: "Bio-Techne Corporation",     tier: "CLEARED",    color: "#1E8449" },
  { name: "Sangon Biotech Co., Ltd.",   tier: "PROHIBITED", color: "#C0392B" },
  { name: "Thermo Electron (Shanghai)", tier: "HIGH RISK",  color: "#D68910" },
  { name: "NovaBio Diagnostics",        tier: "CLEARED",    color: "#1E8449" },
  { name: "BioLink Technologies",       tier: "REVIEW",     color: "#B7950B" },
]

// Duplicate for seamless infinite loop
const TRACK = [...ENTRIES, ...ENTRIES]

export function EntityTicker() {
  return (
    <div
      className="relative border-y border-[#1E1F23] bg-[#090909] py-3.5 overflow-hidden"
      aria-label="Live entity screening feed"
    >
      {/* Fade edges */}
      <div className="pointer-events-none absolute left-0 top-0 h-full w-24 z-10"
        style={{ background: "linear-gradient(to right, #090909, transparent)" }} />
      <div className="pointer-events-none absolute right-0 top-0 h-full w-24 z-10"
        style={{ background: "linear-gradient(to left, #090909, transparent)" }} />

      <div
        className="flex whitespace-nowrap select-none"
        style={{ animation: "entity-marquee 80s linear infinite" }}
      >
        {TRACK.map((entry, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-3 pr-10"
          >
            <span className="font-mono text-[11px] text-[#3A3A3E]">
              {entry.name}
            </span>
            <span
              className="font-mono text-[9px] tracking-[0.18em] uppercase"
              style={{ color: entry.color }}
            >
              {entry.tier}
            </span>
            <span className="font-mono text-[11px] text-[#1E1F23]">·</span>
          </span>
        ))}
      </div>
    </div>
  )
}
