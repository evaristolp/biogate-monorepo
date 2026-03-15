"use client"

import { useScrollReveal } from "@/hooks/use-scroll-reveal"

const weAre = [
  {
    title: "Pre-audit screening",
    body: "BioGate produces structured screening reports. We surface what's there, document how we found it, and hand the analysis to qualified counsel.",
  },
  {
    title: "A tool designed for attorney workflow",
    body: "Every report includes match methodology, confidence scoring, and scope limitation language. Built for the associate who will review it next.",
  },
  {
    title: "Speed infrastructure for a mandatory market",
    body: "The BIOSECURE Act is signed law. The OMB deadline is December 2026. BioGate gives your team a defensible starting point before that clock runs out.",
  },
  {
    title: "An ongoing monitoring layer",
    body: "Watchlists change. New entities are added. BioGate refreshes daily so your compliance posture reflects the current regulatory environment, not last quarter's.",
  },
]

const weAreNot = [
  {
    title: "Legal advice",
    body: "BioGate does not produce legal opinions. Our output has analytical authority. Legal authority comes from the attorney who reviews it.",
  },
  {
    title: "A replacement for counsel",
    body: "We make attorneys faster. The legal judgment, client communication, and remediation strategy are theirs. Not ours.",
  },
  {
    title: "A guarantee of BIOSECURE compliance",
    body: "The OMB BCC list does not exist yet. We screen against the best available proxy watchlists. We disclose this in every report.",
  },
  {
    title: "A dashboard product",
    body: "The report is the deliverable. We don't lead with 'log into our platform.' We lead with 'here's what we found in your vendor data.'",
  },
]

export function WhatWeAre() {
  const headerRef = useScrollReveal<HTMLDivElement>()
  const colsRef = useScrollReveal<HTMLDivElement>()

  return (
    <section className="bg-[#090909] px-6 py-28">
      <div className="mx-auto max-w-[1200px]">

        {/* Header */}
        <div ref={headerRef} className="reveal mb-16">
          <div className="flex items-center gap-3 mb-4">
            <div className="h-px w-8 bg-[#C9A96E]" />
            <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-[#C9A96E]">
              Clarity
            </span>
          </div>
          <h2 className="font-display text-[36px] font-normal leading-tight text-[#F0EEE8] md:text-[44px]">
            What BioGate is.
            <br />
            <span className="text-[#585858]">What BioGate is not.</span>
          </h2>
          <p className="mt-4 max-w-lg text-[16px] text-[#909090]">
            We believe the most credible thing we can do is be precise about
            what our screening reports actually are, and where the line is.
          </p>
        </div>

        {/* Two columns */}
        <div ref={colsRef} className="reveal grid gap-px border border-[#1E1F23] bg-[#1E1F23] md:grid-cols-2">

          {/* What we are */}
          <div className="bg-[#090909] p-8 md:p-10">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#C9A96E] mb-6">
              What we are
            </p>
            <ul className="space-y-7">
              {weAre.map((item) => (
                <li key={item.title}>
                  <p className="text-[14px] font-medium text-[#F0EEE8] mb-1">
                    {item.title}
                  </p>
                  <p className="text-[13px] leading-relaxed text-[#8A8A90]">
                    {item.body}
                  </p>
                </li>
              ))}
            </ul>
          </div>

          {/* What we are not */}
          <div className="bg-[#090909] p-8 md:p-10 md:border-l border-[#1E1F23]">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[#585858] mb-6">
              What we are not
            </p>
            <ul className="space-y-7">
              {weAreNot.map((item) => (
                <li key={item.title}>
                  <p className="text-[14px] font-medium text-[#7A7A80] mb-1">
                    {item.title}
                  </p>
                  <p className="text-[13px] leading-relaxed text-[#585858]">
                    {item.body}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  )
}
