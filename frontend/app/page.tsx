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
      <div id="hero" className="relative min-h-dvh overflow-hidden [contain:layout_paint]">
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

      {/* Brutalist footer statement */}
      <div className="border-t border-[#1E1F23] bg-[#090909] overflow-hidden">
        <div className="px-5 pt-16 pb-10">
          <p className="font-display font-normal leading-[0.86] tracking-[-0.03em] text-[#F0EEE8] uppercase"
            style={{ fontSize: "clamp(2.8rem, 10.5vw, 13rem)" }}>
            Compliance<br />
            intel for the<br />
            next generation.
          </p>
        </div>

        {/* Minimal legal strip */}
        <div className="border-t border-[#1E1F23] px-5 py-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-sans text-[11px] uppercase tracking-[0.2em] text-[#2A2A2E]">
            © 2026 Biogate, Inc.
          </p>
          <div className="flex gap-6 text-[11px] uppercase tracking-[0.18em] text-[#2A2A2E]">
            <Link href="#" className="transition-colors hover:text-[#585858]">Privacy</Link>
            <Link href="#" className="transition-colors hover:text-[#585858]">Terms</Link>
          </div>
          <p className="font-sans text-[11px] uppercase tracking-[0.18em] text-[#2A2A2E]">
            Pre-audit analysis. Not legal advice.
          </p>
        </div>
      </div>
    </div>
  )
}
