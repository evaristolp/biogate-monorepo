import { Lock, Shield, Database } from "lucide-react"

const items = [
  { icon: Lock, label: "TLS 1.3 encrypted" },
  { icon: Shield, label: "Zero prompt injection risk" },
  { icon: Database, label: "No model training on your data" },
]

export function SecurityBanner() {
  return (
    <section
      className="border-b border-border bg-background px-6 py-4"
      aria-label="Security assurances"
    >
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-6 md:gap-10">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex items-center gap-2 text-xs font-medium text-muted-foreground"
          >
            <item.icon className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{item.label}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
