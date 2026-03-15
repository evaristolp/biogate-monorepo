"use client"

import { useEffect, useState, useRef } from "react"

interface Node {
  id: number
  x: number
  y: number
  size: number
  delay: number
}

interface Connection {
  from: number
  to: number
}

export function HeroMesh() {
  const [scrollProgress, setScrollProgress] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  
  // Generate nodes and connections
  const nodeCount = 35
  const nodes: Node[] = []
  const connections: Connection[] = []
  
  // Create nodes in a circular/organic pattern
  for (let i = 0; i < nodeCount; i++) {
    const angle = (i / nodeCount) * Math.PI * 2 + (i % 3) * 0.3
    const radius = 120 + Math.sin(i * 0.8) * 60 + (i % 4) * 25
    const x = 200 + Math.cos(angle) * radius + (Math.sin(i * 2.1) * 30)
    const y = 200 + Math.sin(angle) * radius + (Math.cos(i * 1.7) * 30)
    
    nodes.push({
      id: i,
      x,
      y,
      size: 2 + Math.random() * 3,
      delay: i * 0.1,
    })
  }
  
  // Create connections between nearby nodes
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const dx = nodes[i].x - nodes[j].x
      const dy = nodes[i].y - nodes[j].y
      const distance = Math.sqrt(dx * dx + dy * dy)
      
      if (distance < 100) {
        connections.push({ from: i, to: j })
      }
    }
  }
  
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
  
  return (
    <div
      ref={containerRef}
      className="absolute right-0 top-1/2 -translate-y-1/2 w-[55vw] h-[90vh] pointer-events-none hidden lg:block overflow-hidden"
      style={{
        maskImage: "radial-gradient(ellipse 60% 60% at 50% 50%, black 20%, transparent 70%)",
        WebkitMaskImage: "radial-gradient(ellipse 60% 60% at 50% 50%, black 20%, transparent 70%)",
        transform: `translateY(calc(-50% + ${scrollProgress * 100}px))`,
        opacity: 1 - scrollProgress * 0.5,
      }}
    >
      <svg
        viewBox="0 0 400 400"
        className="w-full h-full"
        style={{
          transform: `rotate(${scrollProgress * 30}deg) scale(${1 - scrollProgress * 0.1})`,
          transition: "transform 0.1s ease-out",
        }}
      >
        {/* Animated connections */}
        <g className="animate-pulse" style={{ animationDuration: "4s" }}>
          {connections.map((conn, i) => (
            <line
              key={`conn-${i}`}
              x1={nodes[conn.from].x}
              y1={nodes[conn.from].y}
              x2={nodes[conn.to].x}
              y2={nodes[conn.to].y}
              stroke="#C9A96E"
              strokeWidth="0.5"
              strokeOpacity="0.15"
              className="animate-pulse"
              style={{ animationDelay: `${i * 0.05}s`, animationDuration: "3s" }}
            />
          ))}
        </g>
        
        {/* Geometric rings */}
        <circle
          cx="200"
          cy="200"
          r="160"
          fill="none"
          stroke="#C9A96E"
          strokeWidth="0.5"
          strokeOpacity="0.08"
          strokeDasharray="4 8"
          className="origin-center animate-spin"
          style={{ animationDuration: "60s" }}
        />
        <circle
          cx="200"
          cy="200"
          r="120"
          fill="none"
          stroke="#C9A96E"
          strokeWidth="0.5"
          strokeOpacity="0.06"
          strokeDasharray="2 6"
          className="origin-center animate-spin"
          style={{ animationDuration: "45s", animationDirection: "reverse" }}
        />
        <circle
          cx="200"
          cy="200"
          r="80"
          fill="none"
          stroke="#C9A96E"
          strokeWidth="0.5"
          strokeOpacity="0.1"
          className="origin-center animate-spin"
          style={{ animationDuration: "30s" }}
        />
        
        {/* Hexagonal core */}
        <polygon
          points="200,160 234,180 234,220 200,240 166,220 166,180"
          fill="none"
          stroke="#C9A96E"
          strokeWidth="0.8"
          strokeOpacity="0.12"
          className="origin-center animate-pulse"
          style={{ animationDuration: "2s" }}
        />
        
        {/* Animated nodes */}
        {nodes.map((node) => (
          <g key={node.id}>
            {/* Glow effect */}
            <circle
              cx={node.x}
              cy={node.y}
              r={node.size * 2}
              fill="#C9A96E"
              fillOpacity="0.05"
              className="animate-pulse"
              style={{ animationDelay: `${node.delay}s`, animationDuration: "2s" }}
            />
            {/* Node */}
            <circle
              cx={node.x}
              cy={node.y}
              r={node.size}
              fill="#C9A96E"
              fillOpacity="0.6"
              className="animate-pulse"
              style={{ animationDelay: `${node.delay}s`, animationDuration: "2.5s" }}
            />
          </g>
        ))}
        
        {/* Central accent */}
        <circle
          cx="200"
          cy="200"
          r="8"
          fill="#C9A96E"
          fillOpacity="0.2"
          className="animate-ping"
          style={{ animationDuration: "3s" }}
        />
        <circle
          cx="200"
          cy="200"
          r="4"
          fill="#C9A96E"
          fillOpacity="0.4"
        />
      </svg>
    </div>
  )
}
