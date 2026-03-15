import { Navbar } from "@/components/navbar"
import { HeroSection } from "@/components/hero-section"
import { EntityTicker } from "@/components/entity-ticker"
import { ProcessFlow } from "@/components/process-flow"
import { DashboardMock } from "@/components/dashboard-mock"
import { WhatWeAre } from "@/components/what-we-are"
import { TrustSecurity } from "@/components/trust-security"
import { FinalCta } from "@/components/final-cta"
import { HeroVisual } from "@/components/hero-visual"
import Link from "next/link"
import { HeatmapMeshLoader } from "@/components/heatmap-mesh-loader"

export default function Home() {
  return (
    <div className="relative min-h-screen bg-[#090909]">
      {/* Three.js heatmap — fixed behind all content */}
      <HeatmapMeshLoader />
      <Navbar />

      {/* 1 — Hero */}
      <div className="relative min-h-dvh overflow-hidden [contain:layout_paint]">
        {/* Very subtle warm radial — barely visible, not decorative */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_30%_40%,rgba(201,169,110,0.04)_0%,transparent_65%)]" />
        <HeroVisual />
        <div className="relative z-10 flex min-h-dvh flex-col justify-center">
          <HeroSection />
        </div>
      </div>

      {/* 2 — Live entity screening feed */}
      <EntityTicker />

      {/* 3 — Process flow */}
      <ProcessFlow />

      {/* 4 — Intelligence report mock */}
      <DashboardMock />

      {/* 5 — What we are / what we're not */}
      <WhatWeAre />

      {/* 6 — Trust & security */}
      <TrustSecurity />

      {/* 7 — Final CTA */}
      <FinalCta />

      {/* Footer */}
      <footer className="border-t border-[#1E1F23] bg-[#090909] px-6 pb-10 pt-14">
        <div className="mx-auto max-w-[1200px]">
          <div className="flex flex-col gap-8 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="flex items-center gap-2.5">
                <svg width="20" height="20" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                  <path d="M16 3L4 8v8c0 7 5.3 13.5 12 15 6.7-1.5 12-8 12-15V8L16 3z" stroke="#C9A96E" strokeWidth="1.6" strokeLinejoin="round" />
                  <line x1="11" y1="12" x2="11" y2="22" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
                  <line x1="16" y1="10" x2="16" y2="22" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
                  <line x1="21" y1="12" x2="21" y2="22" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
                  <line x1="10" y1="17" x2="22" y2="17" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
                  <circle cx="11" cy="17" r="1.4" fill="#C9A96E" />
                  <circle cx="16" cy="17" r="1.4" fill="#C9A96E" />
                  <circle cx="21" cy="17" r="1.4" fill="#C9A96E" />
                </svg>
                <span className="font-display text-[16px] font-normal text-[#F0EEE8]">BioGate</span>
              </div>
              <p className="mt-2 max-w-xs text-[13px] leading-relaxed text-[#3A3A3E]">
                Compliance intelligence for the next generation.
              </p>
            </div>
            <div className="flex gap-8 text-[13px] text-[#3A3A3E]">
              <Link href="#" className="transition-colors hover:text-[#585858]">Privacy</Link>
              <Link href="#" className="transition-colors hover:text-[#585858]">Terms</Link>
              <Link href="#" className="transition-colors hover:text-[#585858]">Contact</Link>
            </div>
          </div>
          <div className="mt-10 border-t border-[#1E1F23] pt-6 flex items-center justify-between">
            <p className="text-[11px] text-[#2A2A2E]">
              {"© 2026 BioGate, Inc. · biogate.us"}
            </p>
            <p className="text-[11px] text-[#2A2A2E]">
              BioGate produces pre-audit intelligence, not legal advice.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
