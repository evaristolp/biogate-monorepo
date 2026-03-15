"use client"

import { useEffect, useRef } from "react"

/**
 * Attaches an IntersectionObserver to the returned ref.
 * When the element enters the viewport, adds the "visible" class,
 * which triggers the CSS fade-up transitions defined in globals.css.
 */
export function useScrollReveal<T extends HTMLElement = HTMLElement>(
  options?: IntersectionObserverInit
) {
  const ref = useRef<T>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("visible")
          observer.unobserve(el)
        }
      },
      { threshold: 0.12, ...options }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [options])

  return ref
}
