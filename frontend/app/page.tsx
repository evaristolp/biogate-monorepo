import { Navbar } from "@/components/navbar"
import { HeroSection } from "@/components/hero-section"
import { EntityTicker } from "@/components/entity-ticker"
import { ProcessFlow } from "@/components/process-flow"
import { DashboardMock } from "@/components/dashboard-mock"
import { WhatWeAre } from "@/components/what-we-are"
import { TrustSecurity } from "@/components/trust-security"
import { FinalCta } from "@/components/final-cta"
import { HeroVisual } from "@/components/hero-visual"
import { HeroMeshWrapper } from "@/components/hero-mesh-wrapper"
import Link from "next/link"

export default function Home() {
  return (
    <div className="min-h-screen bg-[#090909]">
      <Navbar />

      {/* 1 — Hero */}
      <div className="relative min-h-dvh overflow-hidden bg-[#090909] [contain:layout_paint]">
        {/* Very subtle warm radial — barely visible, not decorative */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_30%_40%,rgba(201,169,110,0.04)_0%,transparent_65%)]" />
        <HeroVisual />
        <HeroMeshWrapper />
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
      <footer className="bg-[#090909] px-6 pt-16 pb-8">
        <div className="mx-auto max-w-[1200px]">
          {/* Footer links grid */}
          <div className="flex flex-col gap-8 pb-16 border-b border-[#1E1F23] sm:flex-row sm:justify-between">
            {/* Copyright */}
            <p className="text-[14px] text-[#585858]">
              © BioGate 2026
            </p>
            
            {/* Links */}
            <div className="flex flex-col gap-3 sm:flex-row sm:gap-8">
              <Link href="#" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">Privacy Policy</Link>
              <Link href="#" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">Terms of Use</Link>
            </div>
            
            {/* Contact */}
            <div className="flex flex-col gap-3 sm:flex-row sm:gap-8">
              <a href="mailto:evaristo@biogate.us" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">evaristo@biogate.us</a>
              <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">LinkedIn</a>
            </div>
          </div>
          
          {/* Large BIOGATE wordmark */}
          <div className="pt-10 pb-4 flex justify-center overflow-hidden">
            <span className="text-[48px] sm:text-[64px] md:text-[80px] lg:text-[100px] font-semibold tracking-[0.12em] text-[#1A1A1E] uppercase select-none">
              biogate
            </span>
          </div>
        </div>
      </footer>
    </div>
  )
}
