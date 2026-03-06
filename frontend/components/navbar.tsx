"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { useEffect, useState } from "react"

export function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function onScroll() {
      // Switch when we've scrolled past ~85% of viewport (hero area)
      setScrolled(window.scrollY > window.innerHeight * 0.75)
    }
    onScroll()
    window.addEventListener("scroll", onScroll, { passive: true })
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
        scrolled
          ? "bg-background/90 shadow-sm backdrop-blur-xl"
          : "bg-transparent backdrop-blur-md"
      }`}
    >
      <nav
        className="flex items-center justify-between px-8 py-4"
        aria-label="Main navigation"
      >
        <Link
          href="/"
          className={`text-3xl font-extralight tracking-wide transition-colors duration-500 ${
            scrolled ? "text-foreground" : "text-white"
          }`}
        >
          biogate
        </Link>
        <div className="flex flex-col items-end gap-2 sm:flex-row sm:items-center sm:gap-5">
          <Link
            href="/auth/login"
            className={`text-sm transition-colors duration-500 ${
              scrolled
                ? "text-muted-foreground hover:text-foreground"
                : "text-white/60 hover:text-white"
            }`}
          >
            Log in
          </Link>
          <Link href="/auth/sign-up">
            <Button
              size="sm"
              className={`rounded-full px-5 text-sm font-medium transition-all duration-500 ${
                scrolled
                  ? "bg-foreground text-background hover:bg-foreground/90"
                  : "bg-white text-foreground hover:bg-white/90"
              }`}
            >
              Get started
            </Button>
          </Link>
        </div>
      </nav>
    </header>
  )
}
