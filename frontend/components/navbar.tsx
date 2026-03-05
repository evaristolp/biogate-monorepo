"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"

export function Navbar() {
  return (
    <header className="bg-primary">
      <nav
        className="flex items-center justify-between px-8 py-5"
        aria-label="Main navigation"
      >
        <Link
          href="/"
          className="text-3xl font-extrabold tracking-tight text-primary-foreground"
        >
          biogate
        </Link>
        <div className="flex flex-col items-end gap-2 sm:flex-row sm:items-center sm:gap-5">
          <Link
            href="/signin"
            className="text-sm text-primary-foreground/60 transition-colors hover:text-primary-foreground"
          >
            Log in
          </Link>
          <Button
            size="sm"
            className="rounded-full bg-primary-foreground px-5 text-sm font-medium text-primary hover:bg-primary-foreground/90"
          >
            Get started
          </Button>
        </div>
      </nav>
    </header>
  )
}
