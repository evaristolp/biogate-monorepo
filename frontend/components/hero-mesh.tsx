"use client"

import { useEffect, useState, useRef } from "react"

interface Node {
  id: number
  x: number
  y: number
  z: number
  size: number
}

interface Connection {
  from: number
  to: number
}

export function HeroMesh() {
  const [scrollProgress, setScrollProgress] = useState(0)
  const [time, setTime] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  
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
  
  useEffect(() => {
    let animationId: number
    const animate = () => {
      setTime(t => t + 0.008)
      animationId = requestAnimationFrame(animate)
    }
    animationId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationId)
  }, [])

  // Brutalist grid-based network - isometric 3D projection
  const gridSize = 5
  const spacing = 50
  const nodes: Node[] = []
  const connections: Connection[] = []
  
  // Create a 3D grid of points
  for (let layer = 0; layer < 3; layer++) {
    for (let row = 0; row < gridSize; row++) {
      for (let col = 0; col < gridSize; col++) {
        // Skip some nodes for organic feel
        if ((row + col + layer) % 3 === 0 && layer > 0) continue
        
        // Isometric projection
        const isoX = (col - row) * spacing * 0.7
        const isoY = (col + row) * spacing * 0.4 - layer * spacing * 0.8
        const z = 1 - layer * 0.3 - (row + col) * 0.03
        
        nodes.push({
          id: nodes.length,
          x: 300 + isoX,
          y: 320 + isoY,
          z: Math.max(0.2, z),
          size: 2 + z * 2,
        })
      }
    }
  }
  
  // Connect adjacent nodes - grid pattern
  nodes.forEach((node, i) => {
    nodes.forEach((other, j) => {
      if (i >= j) return
      const dist = Math.sqrt(
        Math.pow(node.x - other.x, 2) + Math.pow(node.y - other.y, 2)
      )
      // Connect if close enough
      if (dist < spacing * 1.2 && dist > 10) {
        connections.push({ from: i, to: j })
      }
    })
  })

  // Animate positions slightly
  const animatedNodes = nodes.map((node) => {
    const drift = Math.sin(time * 0.5 + node.id * 0.3) * 1.5
    const driftY = Math.cos(time * 0.4 + node.id * 0.2) * 1
    return {
      ...node,
      x: node.x + drift,
      y: node.y + driftY,
    }
  })

  return (
    <div
      ref={containerRef}
      className="absolute right-[-10vw] bottom-[5vh] w-[70vw] h-[80vh] pointer-events-none hidden lg:block"
      style={{
        maskImage: "linear-gradient(to left, black 20%, transparent 85%), linear-gradient(to top, black 40%, transparent 90%)",
        WebkitMaskImage: "linear-gradient(to left, black 20%, transparent 85%), linear-gradient(to top, black 40%, transparent 90%)",
        maskComposite: "intersect",
        WebkitMaskComposite: "source-in",
        transform: `translateY(${scrollProgress * 100}px)`,
        opacity: 1 - scrollProgress * 0.7,
      }}
    >
      <svg
        viewBox="0 0 600 500"
        className="w-full h-full"
        style={{
          transform: `rotateZ(${scrollProgress * 8}deg)`,
          transition: "transform 0.2s ease-out",
        }}
      >
        {/* Harsh grid lines - brutalist aesthetic */}
        {connections.map((conn, i) => {
          const fromNode = animatedNodes[conn.from]
          const toNode = animatedNodes[conn.to]
          if (!fromNode || !toNode) return null
          
          const avgZ = (fromNode.z + toNode.z) / 2
          
          return (
            <line
              key={`conn-${i}`}
              x1={fromNode.x}
              y1={fromNode.y}
              x2={toNode.x}
              y2={toNode.y}
              stroke="#C9A96E"
              strokeWidth={avgZ * 1.2}
              strokeOpacity={avgZ * 0.5}
            />
          )
        })}
        
        {/* Sharp rectangular nodes - no soft circles */}
        {animatedNodes
          .sort((a, b) => a.z - b.z)
          .map((node) => {
            const size = node.size * 1.5
            return (
              <g key={node.id}>
                {/* Square node */}
                <rect
                  x={node.x - size / 2}
                  y={node.y - size / 2}
                  width={size}
                  height={size}
                  fill="#C9A96E"
                  fillOpacity={node.z * 0.8}
                />
                {/* Inner highlight for depth */}
                {node.z > 0.7 && (
                  <rect
                    x={node.x - size / 4}
                    y={node.y - size / 4}
                    width={size / 2}
                    height={size / 2}
                    fill="#F0EEE8"
                    fillOpacity={0.4}
                  />
                )}
              </g>
            )
          })}
        
        {/* Horizontal scan lines for texture */}
        {[...Array(12)].map((_, i) => (
          <line
            key={`scan-${i}`}
            x1="100"
            y1={180 + i * 25}
            x2="500"
            y2={180 + i * 25}
            stroke="#C9A96E"
            strokeWidth="0.5"
            strokeOpacity="0.04"
          />
        ))}
        
        {/* Vertical accent lines */}
        {[...Array(8)].map((_, i) => (
          <line
            key={`vert-${i}`}
            x1={180 + i * 35}
            y1="150"
            x2={180 + i * 35}
            y2="450"
            stroke="#C9A96E"
            strokeWidth="0.3"
            strokeOpacity="0.03"
          />
        ))}
      </svg>
    </div>
  )
}
