"use client"

import { useEffect, useState, useRef, useMemo } from "react"

interface Node {
  id: number
  x: number
  y: number
  z: number // depth for 3D effect
  size: number
  delay: number
  tier: "core" | "primary" | "secondary" | "tertiary"
}

interface Connection {
  from: number
  to: number
  strength: number
}

export function HeroMesh() {
  const [scrollProgress, setScrollProgress] = useState(0)
  const [time, setTime] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  
  // Generate a 3D supply chain network
  const { nodes, connections } = useMemo(() => {
    const nodes: Node[] = []
    const connections: Connection[] = []
    
    // Core node (the company)
    nodes.push({
      id: 0,
      x: 300,
      y: 280,
      z: 1,
      size: 8,
      delay: 0,
      tier: "core",
    })
    
    // Primary suppliers/partners (tier 1) - closer, larger
    const primaryCount = 6
    for (let i = 0; i < primaryCount; i++) {
      const angle = (i / primaryCount) * Math.PI * 2 - Math.PI / 2
      const radius = 80
      nodes.push({
        id: nodes.length,
        x: 300 + Math.cos(angle) * radius,
        y: 280 + Math.sin(angle) * radius * 0.6, // compress Y for perspective
        z: 0.85,
        size: 5,
        delay: i * 0.15,
        tier: "primary",
      })
      // Connect to core
      connections.push({ from: 0, to: nodes.length - 1, strength: 1 })
    }
    
    // Secondary tier - medium distance
    const secondaryCount = 12
    for (let i = 0; i < secondaryCount; i++) {
      const angle = (i / secondaryCount) * Math.PI * 2 + Math.PI / 12
      const radiusVariance = Math.sin(i * 1.5) * 25
      const radius = 160 + radiusVariance
      nodes.push({
        id: nodes.length,
        x: 300 + Math.cos(angle) * radius,
        y: 280 + Math.sin(angle) * radius * 0.55,
        z: 0.65 + Math.random() * 0.1,
        size: 3.5,
        delay: i * 0.1 + 0.3,
        tier: "secondary",
      })
      // Connect to nearest primary
      const nearestPrimary = 1 + (i % primaryCount)
      connections.push({ from: nearestPrimary, to: nodes.length - 1, strength: 0.7 })
      
      // Some secondary-to-secondary connections
      if (i > 0 && Math.random() > 0.5) {
        connections.push({ from: nodes.length - 2, to: nodes.length - 1, strength: 0.4 })
      }
    }
    
    // Tertiary tier - far, small, many
    const tertiaryCount = 24
    for (let i = 0; i < tertiaryCount; i++) {
      const angle = (i / tertiaryCount) * Math.PI * 2 + Math.PI / 24
      const radiusVariance = Math.sin(i * 2.3) * 40
      const radius = 260 + radiusVariance
      nodes.push({
        id: nodes.length,
        x: 300 + Math.cos(angle) * radius,
        y: 280 + Math.sin(angle) * radius * 0.5,
        z: 0.35 + Math.random() * 0.15,
        size: 2,
        delay: i * 0.08 + 0.6,
        tier: "tertiary",
      })
      // Connect to nearest secondary
      const nearestSecondary = 7 + (i % secondaryCount)
      connections.push({ from: nearestSecondary, to: nodes.length - 1, strength: 0.35 })
    }
    
    // Add some cross-connections for complexity
    for (let i = 0; i < 8; i++) {
      const from = 7 + Math.floor(Math.random() * secondaryCount)
      const to = 7 + Math.floor(Math.random() * secondaryCount)
      if (from !== to) {
        connections.push({ from, to, strength: 0.25 })
      }
    }
    
    return { nodes, connections }
  }, [])
  
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY
      const windowHeight = window.innerHeight
      const progress = Math.min(scrollY / windowHeight, 1)
      setScrollProgress(progress)
    }
    
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])
  
  // Animate time for subtle movement
  useEffect(() => {
    let animationId: number
    const animate = () => {
      setTime(t => t + 0.01)
      animationId = requestAnimationFrame(animate)
    }
    animationId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationId)
  }, [])
  
  // Calculate animated node positions
  const animatedNodes = nodes.map((node, i) => {
    const wobble = Math.sin(time + node.delay * 2) * 3
    const wobbleY = Math.cos(time * 0.7 + node.delay * 3) * 2
    return {
      ...node,
      x: node.x + wobble,
      y: node.y + wobbleY,
    }
  })
  
  return (
    <div
      ref={containerRef}
      className="absolute right-[-5vw] top-[55%] -translate-y-1/2 w-[65vw] h-[100vh] pointer-events-none hidden lg:block overflow-hidden"
      style={{
        maskImage: "radial-gradient(ellipse 70% 55% at 50% 50%, black 30%, transparent 75%)",
        WebkitMaskImage: "radial-gradient(ellipse 70% 55% at 50% 50%, black 30%, transparent 75%)",
        transform: `translateY(calc(-45% + ${scrollProgress * 150}px))`,
        opacity: 1 - scrollProgress * 0.6,
      }}
    >
      <svg
        viewBox="0 0 600 560"
        className="w-full h-full"
        style={{
          transform: `rotateX(${15 + scrollProgress * 10}deg) rotateZ(${scrollProgress * 15}deg)`,
          transformStyle: "preserve-3d",
          transition: "transform 0.15s ease-out",
        }}
      >
        {/* Background depth layers */}
        <ellipse
          cx="300"
          cy="300"
          rx="280"
          ry="140"
          fill="none"
          stroke="#C9A96E"
          strokeWidth="0.3"
          strokeOpacity="0.06"
          strokeDasharray="2 8"
        />
        <ellipse
          cx="300"
          cy="290"
          rx="200"
          ry="100"
          fill="none"
          stroke="#C9A96E"
          strokeWidth="0.4"
          strokeOpacity="0.08"
          strokeDasharray="1 6"
        />
        <ellipse
          cx="300"
          cy="280"
          rx="120"
          ry="60"
          fill="none"
          stroke="#C9A96E"
          strokeWidth="0.5"
          strokeOpacity="0.1"
        />
        
        {/* Connections - drawn first so nodes appear on top */}
        {connections.map((conn, i) => {
          const fromNode = animatedNodes[conn.from]
          const toNode = animatedNodes[conn.to]
          const avgZ = (fromNode.z + toNode.z) / 2
          
          return (
            <line
              key={`conn-${i}`}
              x1={fromNode.x}
              y1={fromNode.y}
              x2={toNode.x}
              y2={toNode.y}
              stroke="#C9A96E"
              strokeWidth={0.5 + avgZ * 0.8}
              strokeOpacity={0.08 + conn.strength * avgZ * 0.25}
              style={{
                filter: avgZ > 0.7 ? "none" : `blur(${(1 - avgZ) * 0.5}px)`,
              }}
            />
          )
        })}
        
        {/* Nodes - sorted by z-depth for proper layering */}
        {animatedNodes
          .sort((a, b) => a.z - b.z)
          .map((node) => {
            const opacity = 0.3 + node.z * 0.7
            const blur = node.z < 0.5 ? (0.5 - node.z) * 2 : 0
            const scale = 0.6 + node.z * 0.5
            
            return (
              <g key={node.id} style={{ filter: blur > 0 ? `blur(${blur}px)` : "none" }}>
                {/* Outer glow */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.size * scale * 3}
                  fill="#C9A96E"
                  fillOpacity={opacity * 0.08}
                />
                {/* Mid glow */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.size * scale * 1.8}
                  fill="#C9A96E"
                  fillOpacity={opacity * 0.15}
                />
                {/* Core */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.size * scale}
                  fill="#C9A96E"
                  fillOpacity={opacity}
                />
                {/* Highlight for front nodes */}
                {node.z > 0.8 && (
                  <circle
                    cx={node.x - node.size * 0.2}
                    cy={node.y - node.size * 0.2}
                    r={node.size * scale * 0.4}
                    fill="#F0EEE8"
                    fillOpacity={0.3}
                  />
                )}
              </g>
            )
          })}
        
        {/* Central pulse for core company */}
        <circle
          cx={animatedNodes[0].x}
          cy={animatedNodes[0].y}
          r="20"
          fill="#C9A96E"
          fillOpacity="0.05"
          className="animate-ping"
          style={{ animationDuration: "3s", transformOrigin: `${animatedNodes[0].x}px ${animatedNodes[0].y}px` }}
        />
      </svg>
    </div>
  )
}
