import { FileUp, Search, FileCheck, ArrowRight } from "lucide-react"

const steps = [
  {
    icon: FileUp,
    number: "01",
    title: "Drop your data",
    description:
      "Upload CSVs, PDFs, purchase orders, or LIMS exports. We handle the formatting.",
  },
  {
    icon: Search,
    number: "02",
    title: "Instant screening",
    description:
      "Every vendor and parent company cross-referenced against BIS, OFAC, and UFLPA entity lists.",
  },
  {
    icon: FileCheck,
    number: "03",
    title: "Get your report",
    description:
      "Risk Report delivered to your inbox. Attach it to your federal grant paperwork in seconds.",
  },
]

export function HowItWorks() {
  return (
    <section id="how-it-works" className="bg-background px-6 py-24 scroll-mt-20">
      <div className="mx-auto max-w-5xl">
        <p className="text-center text-xs font-semibold uppercase tracking-[0.2em] text-primary">
          How it works
        </p>
        <h2 className="mt-3 text-center text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          <span className="inline-flex items-center gap-3">
            Messy Data <ArrowRight className="h-7 w-7 text-primary" aria-label="to" /> Risk Report
          </span>
        </h2>
        <div className="mt-16 grid gap-10 md:grid-cols-3 md:gap-6">
          {steps.map((step) => (
            <div
              key={step.number}
              className="group rounded-xl border border-border bg-gradient-to-b from-card to-card p-6 transition-all hover:border-primary/30 hover:from-primary/5 hover:to-card"
            >
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <step.icon
                    className="h-5 w-5 text-primary"
                    aria-hidden="true"
                  />
                </div>
                <span className="font-mono text-xs text-muted-foreground">
                  {step.number}
                </span>
              </div>
              <h3 className="mt-4 text-base font-semibold text-foreground">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
