"use client"

import Link from "next/link"
import { useEffect, useState, useRef } from "react"

const EMAIL = "evaristo@biogate.us"

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [contactHovered, setContactHovered] = useState(false)
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

  function handleContactClick() {
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
        {/* Wordmark */}
        <Link href="/" className="group">
          <span className="text-[15px] font-medium tracking-[0.08em] text-[#909090] uppercase transition-colors group-hover:text-[#C9A96E]">
            biogate
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
          <button
            type="button"
            onMouseEnter={() => setContactHovered(true)}
            onMouseLeave={() => setContactHovered(false)}
            onClick={handleContactClick}
            className="relative overflow-hidden rounded-full border border-[#C9A96E]/30 px-6 py-2.5 text-[13px] font-medium text-[#C9A96E] transition-all duration-200 hover:border-[#C9A96E]/60 hover:bg-[#C9A96E]/5 min-w-[160px]"
            aria-label="Copy email address"
          >
            <span
              className={`flex items-center justify-center transition-all duration-200 ${
                contactHovered ? "opacity-0 -translate-y-1.5" : "opacity-100 translate-y-0"
              }`}
            >
              Contact
            </span>
            <span
              className={`absolute inset-0 flex items-center justify-center text-[12px] tracking-wide transition-all duration-200 ${
                contactHovered ? "opacity-100 translate-y-0" : "opacity-0 translate-y-1.5"
              }`}
            >
              {copied ? "Copied" : EMAIL}
            </span>
          </button>
        </div>
      </nav>
    </header>
  )
}
