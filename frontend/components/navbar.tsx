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
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <svg width="26" height="26" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M16 3L4 8v8c0 7 5.3 13.5 12 15 6.7-1.5 12-8 12-15V8L16 3z" stroke="#C9A96E" strokeWidth="1.6" strokeLinejoin="round" />
            <line x1="11" y1="12" x2="11" y2="22" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
            <line x1="16" y1="10" x2="16" y2="22" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
            <line x1="21" y1="12" x2="21" y2="22" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
            <line x1="10" y1="17" x2="22" y2="17" stroke="#C9A96E" strokeWidth="1.4" strokeLinecap="round" />
            <circle cx="11" cy="17" r="1.4" fill="#C9A96E" />
            <circle cx="16" cy="17" r="1.4" fill="#C9A96E" />
            <circle cx="21" cy="17" r="1.4" fill="#C9A96E" />
          </svg>
          <span className="font-display text-[18px] font-normal tracking-tight text-[#F0EEE8] transition-colors group-hover:text-[#C9A96E]">
            BioGate
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
            className="relative overflow-hidden rounded-sm border border-[#C9A96E]/40 px-5 py-2 text-sm font-medium text-[#C9A96E] transition-all hover:border-[#C9A96E] hover:bg-[#C9A96E]/5 min-w-[130px]"
            aria-label="Copy email address"
          >
            <span
              className={`flex items-center justify-center transition-all duration-300 ${
                contactHovered ? "opacity-0 -translate-y-2" : "opacity-100 translate-y-0"
              }`}
            >
              Contact
            </span>
            <span
              className={`absolute inset-0 flex items-center justify-center font-mono text-[10px] tracking-[0.08em] transition-all duration-300 ${
                contactHovered ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
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
