"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

const CALENDAR_URL = "https://calendar.app.google/jWgYSizJdFhYJKUU9"

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > window.innerHeight * 0.75)
    }
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

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
          <a
            href={CALENDAR_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full border border-[#C9A96E]/30 px-6 py-2.5 text-[13px] font-medium text-[#C9A96E] transition-all duration-200 hover:border-[#C9A96E]/60 hover:bg-[#C9A96E]/5"
          >
            Schedule Demo
          </a>
        </div>
      </nav>
    </header>
  )
}
