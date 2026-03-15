"use client"

import Link from "next/link"
import { useEffect, useState, useRef } from "react"

const EMAIL = "info@biogate.us"

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const copyTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > window.innerHeight * 0.75)
    }
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  function handleCopy() {
    navigator.clipboard.writeText(EMAIL).then(() => {
      setCopied(true)
      if (copyTimeout.current) clearTimeout(copyTimeout.current)
      copyTimeout.current = setTimeout(() => setCopied(false), 1800)
    })
  }

  return (
    <header
      className={`fixed left-0 right-0 top-0 z-50 transition-all duration-500 ${
        scrolled
          ? "border-b border-[#1E1F23] bg-[#090909]/95 backdrop-blur-xl"
          : "bg-transparent"
      }`}
    >
      <nav
        className="mx-auto flex max-w-[1200px] items-center justify-between px-6 py-5"
        aria-label="Main navigation"
      >
        {/* Wordmark — no icon, just the name */}
        <Link href="/" className="group">
          <span className="font-sans text-[13px] font-semibold uppercase tracking-[0.28em] text-[#F0EEE8] transition-opacity group-hover:opacity-60">
            Biogate
          </span>
        </Link>

        {/* Nav */}
        <div className="flex items-center gap-7">
          <Link href="#how-it-works" className="hidden text-sm text-[#585858] transition-colors hover:text-[#909090] sm:block">
            How it works
          </Link>
          <Link href="#security" className="hidden text-sm text-[#585858] transition-colors hover:text-[#909090] sm:block">
            Security
          </Link>
          {/* Contact — hover reveals dropdown with email + copy */}
          <div
            className="relative"
            onMouseEnter={() => setDropdownOpen(true)}
            onMouseLeave={() => setDropdownOpen(false)}
          >
            <button
              type="button"
              className="rounded-sm border border-[#C9A96E]/40 px-5 py-2 text-sm font-medium text-[#C9A96E] transition-all hover:border-[#C9A96E] hover:bg-[#C9A96E]/5"
            >
              Contact
            </button>

            {/* Dropdown */}
            <div
              className={`absolute right-0 top-full mt-1.5 z-50 min-w-[220px] overflow-hidden rounded-sm border border-[#C9A96E]/30 bg-[#0D0D0F] transition-all duration-200 ${
                dropdownOpen ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 -translate-y-1 pointer-events-none"
              }`}
            >
              <div className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="font-mono text-[11px] text-[#C9A96E] tracking-[0.06em]">
                  {EMAIL}
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="shrink-0 rounded-sm border border-[#1E1F23] px-3 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[#585858] transition-colors hover:border-[#C9A96E]/40 hover:text-[#C9A96E]"
                >
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </nav>
    </header>
  )
}
