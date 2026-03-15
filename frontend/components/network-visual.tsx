"use client"

import { useEffect, useRef, useCallback } from "react"

interface Node {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  risk: number
  pulsePhase: number
  label: string
  isAnchor: boolean // anchor nodes are larger, labeled
}

const LABELS = [
  "NeuroVex", "AxiomRNA", "CellPath", "Helix Ltd", "NovaBio",
  "GenSync", "SeqWorks", "ProteomX", "VaxCore", "PharmaLnk",
  "OmniGen", "SynBridge", "CryoLab", "TheraPlex", "GeneForge",
  "NanoRx", "Innogen", "ZymoTek", "PrimaGen", "LumiCell",
]

const ANCHOR_COUNT = 20
const WEB_NODE_COUNT = 60 // small unlabeled web-filler nodes (desktop)
const MOBILE_ANCHOR_COUNT = 10
const MOBILE_WEB_NODE_COUNT = 20

function createNodes(width: number, height: number, isMobile: boolean): Node[] {
  const anchorCount = isMobile ? MOBILE_ANCHOR_COUNT : ANCHOR_COUNT
  const webCount = isMobile ? MOBILE_WEB_NODE_COUNT : WEB_NODE_COUNT
  const total = anchorCount + webCount
  const nodes: Node[] = []
  for (let i = 0; i < total; i++) {
    const isAnchor = i < anchorCount
    const risk = Math.random()
    nodes.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * (isAnchor ? 0.066 : 0.11),
      vy: (Math.random() - 0.5) * (isAnchor ? 0.066 : 0.11),
      radius: isAnchor ? 3 + Math.random() * 4 : 1 + Math.random() * 1.5,
      risk,
      pulsePhase: Math.random() * Math.PI * 2,
      label: isAnchor ? LABELS[i % LABELS.length] : "",
      isAnchor,
    })
  }
  return nodes
}

function riskColor(risk: number, alpha: number): string {
  if (risk < 0.35) return `rgba(30, 132, 73, ${alpha})`    // --risk-green  (muted)
  if (risk < 0.55) return `rgba(183, 149, 11, ${alpha})`   // --risk-yellow (muted)
  if (risk < 0.75) return `rgba(214, 137, 16, ${alpha})`   // --risk-amber  (muted)
  return `rgba(192, 57, 43, ${alpha})`                     // --risk-red    (muted)
}

export function NetworkVisual() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseRef = useRef({ x: -1000, y: -1000 })
  const nodesRef = useRef<Node[]>([])
  const animRef = useRef<number>(0)
  const timeRef = useRef(0)
  const isMobileRef = useRef(false)
  const isVisibleRef = useRef(true)
  const lastFrameTimeRef = useRef(0)
  const isScrollingRef = useRef(false)
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isMobileRef.current) return // Disable on mobile
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    mouseRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    }
  }, [])

  // Handle scroll events on mobile - pause animation during scroll
  const handleScroll = useCallback(() => {
    if (!isMobileRef.current) return
    isScrollingRef.current = true
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current)
    }
    scrollTimeoutRef.current = setTimeout(() => {
      isScrollingRef.current = false
    }, 150)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const resize = () => {
      const parent = canvas.parentElement
      if (!parent) return
      const dpr = window.devicePixelRatio || 1
      canvas.width = parent.clientWidth * dpr
      canvas.height = parent.clientHeight * dpr
      canvas.style.width = `${parent.clientWidth}px`
      canvas.style.height = `${parent.clientHeight}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      nodesRef.current = createNodes(parent.clientWidth, parent.clientHeight, isMobileRef.current)
    }

    // Detect mobile/touch device
    isMobileRef.current = window.matchMedia("(pointer: coarse)").matches || 
      window.matchMedia("(max-width: 768px)").matches

    // On mobile, pause animation when scrolled out of view to prevent jank
    let observer: IntersectionObserver | null = null
    if (isMobileRef.current) {
      observer = new IntersectionObserver(
        (entries) => {
          isVisibleRef.current = entries[0]?.isIntersecting ?? true
        },
        { threshold: 0.1 }
      )
      observer.observe(canvas)
    }

    resize()
    window.addEventListener("resize", resize)
    if (!isMobileRef.current) {
      window.addEventListener("mousemove", handleMouseMove)
    } else {
      // On mobile, listen for scroll to pause animation during scrolling
      window.addEventListener("scroll", handleScroll, { passive: true })
    }

    const w = () => canvas.clientWidth
    const h = () => canvas.clientHeight

    const draw = (timestamp: number) => {
      // On mobile, skip rendering when scrolled out of view or during scrolling
      if (isMobileRef.current && (!isVisibleRef.current || isScrollingRef.current)) {
        animRef.current = requestAnimationFrame(draw)
        return
      }

      // Throttle frame rate on mobile to ~30fps for smoother experience
      if (isMobileRef.current) {
        const elapsed = timestamp - lastFrameTimeRef.current
        if (elapsed < 33) { // ~30fps
          animRef.current = requestAnimationFrame(draw)
          return
        }
        lastFrameTimeRef.current = timestamp
      }

      timeRef.current += 0.006
      const t = timeRef.current
      const nodes = nodesRef.current
      const mx = mouseRef.current.x
      const my = mouseRef.current.y

      ctx.clearRect(0, 0, w(), h())

      // Move nodes
      for (const node of nodes) {
        node.x += node.vx
        node.y += node.vy

        // Mouse interaction -- only on desktop
        if (!isMobileRef.current) {
          const dx = node.x - mx
          const dy = node.y - my
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 150 && dist > 0) {
            const force = (150 - dist) / 150
            if (node.isAnchor) {
              node.vx += (dx / dist) * force * 0.03
              node.vy += (dy / dist) * force * 0.03
            } else {
              node.vx -= (dx / dist) * force * 0.008
              node.vy -= (dy / dist) * force * 0.008
            }
          }
        }

        node.vx *= 0.988
        node.vy *= 0.988

        if (node.x < 0 || node.x > w()) node.vx *= -1
        if (node.y < 0 || node.y > h()) node.vy *= -1
        node.x = Math.max(0, Math.min(w(), node.x))
        node.y = Math.max(0, Math.min(h(), node.y))
      }

      // --- Web connections between all nearby nodes ---
      const WEB_DIST = 200
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i]
          const b = nodes[j]
          const ddx = a.x - b.x
          const ddy = a.y - b.y
          const dist = Math.sqrt(ddx * ddx + ddy * ddy)
          if (dist < WEB_DIST) {
            const strength = 1 - dist / WEB_DIST
            const bothAnchor = a.isAnchor && b.isAnchor
            const eitherAnchor = a.isAnchor || b.isAnchor
            const pulse = 0.1 + Math.sin(t * 1.2 + i * 0.3) * 0.05
            const alpha = strength * pulse * (bothAnchor ? 2 : eitherAnchor ? 1.2 : 0.6)
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.strokeStyle = `rgba(201, 169, 110, ${Math.min(alpha, 0.07)})`
            ctx.lineWidth = bothAnchor ? strength * 1.2 : strength * 0.5
            ctx.stroke()
          }
        }
      }

      // --- Heatmap glows on ALL nodes (bigger, softer, overlapping) ---
      for (const node of nodes) {
        const baseRadius = node.isAnchor ? 70 : 35
        const glowRadius = baseRadius + Math.sin(t * 0.8 + node.pulsePhase) * 15
        const glowAlpha = node.isAnchor ? 0.1 : 0.04
        const grad = ctx.createRadialGradient(
          node.x, node.y, 0,
          node.x, node.y, glowRadius
        )
        grad.addColorStop(0, riskColor(node.risk, glowAlpha))
        grad.addColorStop(0.5, riskColor(node.risk, glowAlpha * 0.4))
        grad.addColorStop(1, "transparent")
        ctx.beginPath()
        ctx.arc(node.x, node.y, glowRadius, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()
      }

      // --- Mouse proximity heatmap intensifier (desktop only) ---
      if (!isMobileRef.current) {
        const HEAT_RADIUS = 180
        for (const node of nodes) {
          const ddx = node.x - mx
          const ddy = node.y - my
          const dist = Math.sqrt(ddx * ddx + ddy * ddy)
          if (dist < HEAT_RADIUS) {
            const proximity = 1 - dist / HEAT_RADIUS
            const extraRadius = (node.isAnchor ? 50 : 25) * proximity
            const grad = ctx.createRadialGradient(
              node.x, node.y, 0,
              node.x, node.y, extraRadius + 30
            )
            grad.addColorStop(0, riskColor(node.risk, proximity * 0.15))
            grad.addColorStop(1, "transparent")
            ctx.beginPath()
            ctx.arc(node.x, node.y, extraRadius + 30, 0, Math.PI * 2)
            ctx.fillStyle = grad
            ctx.fill()
          }
        }
      }

      // Draw nodes
      for (const node of nodes) {
        const pulse = 1 + Math.sin(t * 3 + node.pulsePhase) * 0.15
        const r = node.radius * pulse

        if (node.isAnchor) {
          // Outer ring
          ctx.beginPath()
          ctx.arc(node.x, node.y, r + 2, 0, Math.PI * 2)
          ctx.strokeStyle = riskColor(node.risk, 0.25)
          ctx.lineWidth = 1
          ctx.stroke()
        }

        // Core dot
        ctx.beginPath()
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2)
        ctx.fillStyle = node.isAnchor
          ? riskColor(node.risk, 0.8)
          : `rgba(201, 169, 110, ${0.08 + pulse * 0.04})`
        ctx.fill()

        // Label for anchors
        if (node.isAnchor) {
          let labelOpacity = 0.35
          if (!isMobileRef.current) {
            const dxm = node.x - mx
            const dym = node.y - my
            const distm = Math.sqrt(dxm * dxm + dym * dym)
            const hoverBoost = distm < 100 ? Math.max(0, 1 - distm / 100) * 0.55 : 0
            labelOpacity = 0.3 + hoverBoost
          }
          ctx.font = "500 10px var(--font-mono), monospace"
          ctx.fillStyle = `rgba(255, 255, 255, ${labelOpacity})`
          ctx.fillText(node.label, node.x + r + 5, node.y + 3)
        }
      }

      // Scan line
      const scanY = (t * 40) % h()
      ctx.beginPath()
      ctx.moveTo(0, scanY)
      ctx.lineTo(w(), scanY)
      ctx.strokeStyle = "rgba(201, 169, 110, 0.02)"
      ctx.lineWidth = 1
      ctx.stroke()

      animRef.current = requestAnimationFrame(draw)
    }

    animRef.current = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener("resize", resize)
      window.removeEventListener("mousemove", handleMouseMove)
      window.removeEventListener("scroll", handleScroll)
      if (scrollTimeoutRef.current) clearTimeout(scrollTimeoutRef.current)
      if (observer) observer.disconnect()
    }
  }, [handleMouseMove, handleScroll])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 h-full w-full pointer-events-none"
      style={{ 
        touchAction: "none",
        willChange: "transform",
        transform: "translateZ(0)",
        backfaceVisibility: "hidden"
      }}
      aria-hidden="true"
    />
  )
}
