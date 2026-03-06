"use client"

import { useEffect, useRef, useCallback, useState } from "react"

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
const MOBILE_ANCHOR_COUNT = 12
const MOBILE_WEB_NODE_COUNT = 25

// Brand palette colors
const COLORS = {
  green: "#4ADE80",    // Accent Green - low risk
  orange: "#F59E0B",   // Accent Orange - medium risk
  red: "#EF4444",      // Accent Red - high risk
  teal: "#2E8B8B",     // Bright Teal - connections
  midTeal: "#1A4B5C",  // Mid Teal
}

function createNodes(width: number, height: number, isMobile: boolean): Node[] {
  const anchorCount = isMobile ? MOBILE_ANCHOR_COUNT : ANCHOR_COUNT
  const webCount = isMobile ? MOBILE_WEB_NODE_COUNT : WEB_NODE_COUNT
  const total = anchorCount + webCount
  const nodes: Node[] = []
  // Use seeded random for consistent static layout on mobile
  const seed = 12345
  let seededRandom = seed
  const nextRandom = () => {
    seededRandom = (seededRandom * 1103515245 + 12345) & 0x7fffffff
    return seededRandom / 0x7fffffff
  }
  
  for (let i = 0; i < total; i++) {
    const isAnchor = i < anchorCount
    const risk = isMobile ? nextRandom() : Math.random()
    const randX = isMobile ? nextRandom() : Math.random()
    const randY = isMobile ? nextRandom() : Math.random()
    const randVx = isMobile ? nextRandom() : Math.random()
    const randVy = isMobile ? nextRandom() : Math.random()
    const randRadius = isMobile ? nextRandom() : Math.random()
    const randPhase = isMobile ? nextRandom() : Math.random()
    
    nodes.push({
      x: randX * width,
      y: randY * height,
      vx: (randVx - 0.5) * (isAnchor ? 0.066 : 0.11),
      vy: (randVy - 0.5) * (isAnchor ? 0.066 : 0.11),
      radius: isAnchor ? 3 + randRadius * 4 : 1 + randRadius * 1.5,
      risk,
      pulsePhase: randPhase * Math.PI * 2,
      label: isAnchor ? LABELS[i % LABELS.length] : "",
      isAnchor,
    })
  }
  return nodes
}

function riskColor(risk: number, alpha: number): string {
  // Using brand palette colors
  if (risk < 0.35) return `rgba(74, 222, 128, ${alpha})`  // #4ADE80 green
  if (risk < 0.65) return `rgba(245, 158, 11, ${alpha})` // #F59E0B orange
  return `rgba(239, 68, 68, ${alpha})`                    // #EF4444 red
}

// Static visualization component for mobile
function StaticNetworkVisual() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const hasDrawnRef = useRef(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || hasDrawnRef.current) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const parent = canvas.parentElement
    if (!parent) return
    
    const dpr = window.devicePixelRatio || 1
    canvas.width = parent.clientWidth * dpr
    canvas.height = parent.clientHeight * dpr
    canvas.style.width = `${parent.clientWidth}px`
    canvas.style.height = `${parent.clientHeight}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    const w = parent.clientWidth
    const h = parent.clientHeight
    const nodes = createNodes(w, h, true)

    // Draw connections
    const WEB_DIST = 180
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
          const alpha = strength * 0.12 * (bothAnchor ? 2 : eitherAnchor ? 1.2 : 0.6)
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.strokeStyle = `rgba(46, 139, 139, ${Math.min(alpha, 0.15)})` // Bright Teal
          ctx.lineWidth = bothAnchor ? strength * 1.2 : strength * 0.5
          ctx.stroke()
        }
      }
    }

    // Draw heatmap glows
    for (const node of nodes) {
      const baseRadius = node.isAnchor ? 60 : 30
      const glowAlpha = node.isAnchor ? 0.12 : 0.05
      const grad = ctx.createRadialGradient(
        node.x, node.y, 0,
        node.x, node.y, baseRadius
      )
      grad.addColorStop(0, riskColor(node.risk, glowAlpha))
      grad.addColorStop(0.5, riskColor(node.risk, glowAlpha * 0.4))
      grad.addColorStop(1, "transparent")
      ctx.beginPath()
      ctx.arc(node.x, node.y, baseRadius, 0, Math.PI * 2)
      ctx.fillStyle = grad
      ctx.fill()
    }

    // Draw nodes
    for (const node of nodes) {
      const r = node.radius

      if (node.isAnchor) {
        // Outer ring
        ctx.beginPath()
        ctx.arc(node.x, node.y, r + 2, 0, Math.PI * 2)
        ctx.strokeStyle = riskColor(node.risk, 0.3)
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Core dot
      ctx.beginPath()
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2)
      ctx.fillStyle = node.isAnchor
        ? riskColor(node.risk, 0.85)
        : `rgba(46, 139, 139, 0.35)` // Bright Teal for small nodes
      ctx.fill()

      // Label for anchors
      if (node.isAnchor) {
        ctx.font = "500 9px var(--font-mono), monospace"
        ctx.fillStyle = `rgba(255, 255, 255, 0.4)`
        ctx.fillText(node.label, node.x + r + 5, node.y + 3)
      }
    }

    hasDrawnRef.current = true
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 h-full w-full pointer-events-none"
      aria-hidden="true"
    />
  )
}

// Animated visualization for desktop
function AnimatedNetworkVisual() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const mouseRef = useRef({ x: -1000, y: -1000 })
  const nodesRef = useRef<Node[]>([])
  const animRef = useRef<number>(0)
  const timeRef = useRef(0)

  const handleMouseMove = useCallback((e: MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    mouseRef.current = {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    }
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
      nodesRef.current = createNodes(parent.clientWidth, parent.clientHeight, false)
    }

    resize()
    window.addEventListener("resize", resize)
    window.addEventListener("mousemove", handleMouseMove)

    const w = () => canvas.clientWidth
    const h = () => canvas.clientHeight

    const draw = () => {
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

        // Mouse interaction
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
            ctx.strokeStyle = `rgba(46, 139, 139, ${Math.min(alpha, 0.18)})` // Bright Teal
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

      // --- Mouse proximity heatmap intensifier ---
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
          : `rgba(46, 139, 139, ${0.25 + pulse * 0.1})` // Bright Teal
        ctx.fill()

        // Label for anchors
        if (node.isAnchor) {
          const dxm = node.x - mx
          const dym = node.y - my
          const distm = Math.sqrt(dxm * dxm + dym * dym)
          const hoverBoost = distm < 100 ? Math.max(0, 1 - distm / 100) * 0.55 : 0
          const labelOpacity = 0.3 + hoverBoost
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
      ctx.strokeStyle = "rgba(46, 139, 139, 0.04)" // Bright Teal
      ctx.lineWidth = 1
      ctx.stroke()

      animRef.current = requestAnimationFrame(draw)
    }

    animRef.current = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener("resize", resize)
      window.removeEventListener("mousemove", handleMouseMove)
    }
  }, [handleMouseMove])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 h-full w-full pointer-events-none"
      style={{ 
        willChange: "transform",
        transform: "translateZ(0)",
        backfaceVisibility: "hidden"
      }}
      aria-hidden="true"
    />
  )
}

export function NetworkVisual() {
  const [isMobile, setIsMobile] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const checkMobile = () => {
      setIsMobile(
        window.matchMedia("(pointer: coarse)").matches || 
        window.matchMedia("(max-width: 768px)").matches
      )
    }
    checkMobile()
    window.addEventListener("resize", checkMobile)
    return () => window.removeEventListener("resize", checkMobile)
  }, [])

  // SSR fallback - render nothing until mounted
  if (!mounted) return null

  // Render static version on mobile, animated on desktop
  return isMobile ? <StaticNetworkVisual /> : <AnimatedNetworkVisual />
}
