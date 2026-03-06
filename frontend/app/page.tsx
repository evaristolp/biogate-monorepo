import { Navbar } from "@/components/navbar"
import { HeroSection } from "@/components/hero-section"
import { SecurityBanner } from "@/components/security-banner"
import { HowItWorks } from "@/components/how-it-works"
import { NetworkVisual } from "@/components/network-visual"

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      {/* --- Mesh gradient hero with network visual --- */}
      <div className="relative min-h-dvh overflow-hidden bg-[#0B1A2E] [contain:layout_paint] [content-visibility:auto]">
        {/* Layered radial blobs using brand palette */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,#1A4B5C_0%,transparent_50%)] opacity-70" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_75%_20%,#2E8B8B_0%,transparent_45%)] opacity-50" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_60%_80%,#0E2A3F_0%,transparent_50%)] opacity-60" />
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_80%,#1A4B5C_0%,transparent_40%)] opacity-40" />
        {/* Interactive network canvas */}
        <NetworkVisual />
        <div className="relative z-10 flex min-h-dvh flex-col justify-center">
          <HeroSection />
        </div>
      </div>
      <main>
        <SecurityBanner />
        <HowItWorks />
      </main>
      <footer className="bg-[#0B1A2E] px-8 pb-8 pt-16">
        <div className="mx-auto max-w-6xl">
          <div className="flex flex-col gap-8 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-2xl font-extrabold tracking-tight text-white">
                biogate
              </p>
              <p className="mt-2 max-w-sm text-sm leading-relaxed text-white/40">
                Compliance infrastructure for the next generation.
              </p>
            </div>
            <div className="flex gap-8 text-sm text-white/40">
              <a href="#" className="transition-colors hover:text-white/70">
                Privacy
              </a>
              <a href="#" className="transition-colors hover:text-white/70">
                Terms
              </a>
              <a href="#" className="transition-colors hover:text-white/70">
                Contact
              </a>
            </div>
          </div>
          <div className="mt-12 border-t border-white/10 pt-6">
            <p className="text-xs text-white/25">
              {"© 2026 BioGate, Inc. All rights reserved."}
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
