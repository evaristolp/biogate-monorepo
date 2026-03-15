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

export default function Home() {
  return (
    <div className="min-h-screen bg-[#090909]">
      <Navbar />

      {/* 1 — Hero */}
      <div className="relative min-h-dvh overflow-hidden bg-[#090909] [contain:layout_paint]">
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
      <footer className="bg-[#090909] px-6 pt-16 pb-8">
        <div className="mx-auto max-w-[1200px]">
          {/* Footer links grid */}
          <div className="grid grid-cols-3 gap-8 pb-16 border-b border-[#1E1F23]">
            {/* Copyright */}
            <div>
              <p className="text-[14px] text-[#585858]">
                © BioGate 2026
              </p>
            </div>
            
            {/* Links */}
            <div className="flex flex-col gap-3">
              <Link href="#" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">Privacy Policy</Link>
              <Link href="#" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">Terms of Use</Link>
            </div>
            
            {/* Contact */}
            <div className="flex flex-col gap-3">
              <a href="mailto:evaristo@biogate.us" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">evaristo@biogate.us</a>
              <a href="https://linkedin.com" target="_blank" rel="noopener noreferrer" className="text-[14px] text-[#585858] transition-colors hover:text-[#909090]">LinkedIn</a>
            </div>
          </div>
          
          {/* Brutalist BIOGATE wordmark */}
          <div className="pt-16 pb-8 flex justify-center overflow-hidden">
            <svg 
              viewBox="0 0 800 120" 
              className="w-full max-w-[900px] h-auto"
              aria-label="BioGate"
            >
              <defs>
                <pattern id="halftone" patternUnits="userSpaceOnUse" width="8" height="8">
                  <circle cx="4" cy="4" r="2.5" fill="#F0EEE8" />
                </pattern>
              </defs>
              
              {/* B */}
              <rect x="0" y="0" width="20" height="120" fill="#F0EEE8" />
              <rect x="20" y="0" width="60" height="20" fill="#F0EEE8" />
              <rect x="20" y="50" width="50" height="20" fill="#F0EEE8" />
              <rect x="20" y="100" width="60" height="20" fill="#F0EEE8" />
              <rect x="70" y="15" width="20" height="40" fill="#F0EEE8" />
              <rect x="60" y="65" width="20" height="40" fill="#F0EEE8" />
              
              {/* I */}
              <rect x="110" y="0" width="20" height="120" fill="#F0EEE8" />
              
              {/* O */}
              <rect x="150" y="20" width="20" height="80" fill="#F0EEE8" />
              <rect x="210" y="20" width="20" height="80" fill="#F0EEE8" />
              <rect x="165" y="0" width="50" height="20" fill="#F0EEE8" />
              <rect x="165" y="100" width="50" height="20" fill="#F0EEE8" />
              
              {/* G */}
              <rect x="260" y="0" width="80" height="20" fill="#F0EEE8" />
              <rect x="260" y="20" width="20" height="80" fill="#F0EEE8" />
              <rect x="260" y="100" width="80" height="20" fill="#F0EEE8" />
              <rect x="320" y="60" width="20" height="60" fill="#F0EEE8" />
              <rect x="295" y="55" width="45" height="20" fill="#F0EEE8" />
              
              {/* A */}
              <rect x="370" y="20" width="20" height="100" fill="#F0EEE8" />
              <rect x="430" y="20" width="20" height="100" fill="#F0EEE8" />
              <rect x="385" y="0" width="50" height="20" fill="#F0EEE8" />
              <rect x="385" y="55" width="50" height="20" fill="#F0EEE8" />
              
              {/* T */}
              <rect x="470" y="0" width="90" height="20" fill="#F0EEE8" />
              <rect x="500" y="20" width="20" height="100" fill="#F0EEE8" />
              
              {/* E */}
              <rect x="590" y="0" width="20" height="120" fill="#F0EEE8" />
              <rect x="610" y="0" width="60" height="20" fill="#F0EEE8" />
              <rect x="610" y="50" width="45" height="20" fill="#F0EEE8" />
              <rect x="610" y="100" width="60" height="20" fill="#F0EEE8" />
              
              {/* Halftone decorative dots - left side */}
              <circle cx="695" cy="15" r="5" fill="#F0EEE8" />
              <circle cx="710" cy="15" r="5" fill="#F0EEE8" />
              <circle cx="725" cy="15" r="5" fill="#F0EEE8" />
              <circle cx="740" cy="15" r="4" fill="#F0EEE8" />
              <circle cx="753" cy="15" r="3" fill="#F0EEE8" />
              <circle cx="764" cy="15" r="2" fill="#F0EEE8" />
              
              <circle cx="695" cy="35" r="5" fill="#F0EEE8" />
              <circle cx="710" cy="35" r="5" fill="#F0EEE8" />
              <circle cx="725" cy="35" r="5" fill="#F0EEE8" />
              <circle cx="740" cy="35" r="4" fill="#F0EEE8" />
              <circle cx="753" cy="35" r="3" fill="#F0EEE8" />
              
              <circle cx="695" cy="55" r="5" fill="#F0EEE8" />
              <circle cx="710" cy="55" r="5" fill="#F0EEE8" />
              <circle cx="725" cy="55" r="4" fill="#F0EEE8" />
              <circle cx="738" cy="55" r="3" fill="#F0EEE8" />
              
              <circle cx="695" cy="75" r="5" fill="#F0EEE8" />
              <circle cx="710" cy="75" r="5" fill="#F0EEE8" />
              <circle cx="725" cy="75" r="4" fill="#F0EEE8" />
              <circle cx="738" cy="75" r="3" fill="#F0EEE8" />
              
              <circle cx="695" cy="95" r="5" fill="#F0EEE8" />
              <circle cx="710" cy="95" r="5" fill="#F0EEE8" />
              <circle cx="725" cy="95" r="5" fill="#F0EEE8" />
              <circle cx="740" cy="95" r="4" fill="#F0EEE8" />
              <circle cx="753" cy="95" r="3" fill="#F0EEE8" />
              
              <circle cx="695" cy="110" r="5" fill="#F0EEE8" />
              <circle cx="710" cy="110" r="5" fill="#F0EEE8" />
              <circle cx="725" cy="110" r="5" fill="#F0EEE8" />
              <circle cx="740" cy="110" r="4" fill="#F0EEE8" />
              <circle cx="753" cy="110" r="3" fill="#F0EEE8" />
              <circle cx="764" cy="110" r="2" fill="#F0EEE8" />
            </svg>
          </div>
        </div>
      </footer>
    </div>
  )
}
