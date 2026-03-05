import { Navbar } from "@/components/navbar"
import { HeroSection } from "@/components/hero-section"
import { SecurityBanner } from "@/components/security-banner"
import { HowItWorks } from "@/components/how-it-works"
import { AuditUploader } from "@/components/audit-uploader"

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <HeroSection />
        <SecurityBanner />
        <HowItWorks />
        <AuditUploader />
      </main>
      <footer className="border-t border-border bg-background px-6 py-8">
        <p className="text-center text-xs text-muted-foreground">
          {"© 2026 BioGate, Inc."}
        </p>
      </footer>
    </div>
  )
}
