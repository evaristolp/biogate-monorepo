"use client"

// 3D Icosahedron wireframe mesh - pure CSS/SVG, no Three.js
import { useEffect, useState, useMemo } from "react"

interface Point3D {
  x: number
  y: number
  z: number
}

interface Edge {
  from: number
  to: number
}

export function HeroMesh() {
  const [scrollProgress, setScrollProgress] = useState(0)
  const [time, setTime] = useState(0)
  
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY
      const windowHeight = window.innerHeight
      const progress = Math.min(scrollY / (windowHeight * 1.5), 1)
      setScrollProgress(progress)
    }
    
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])
  
  useEffect(() => {
    let animationId: number
    const animate = () => {
      setTime(t => t + 0.003)
      animationId = requestAnimationFrame(animate)
    }
    animationId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationId)
  }, [])

  // Create icosahedron vertices (20 faces, 12 vertices)
  const phi = (1 + Math.sqrt(5)) / 2 // golden ratio
  
  const baseVertices: Point3D[] = useMemo(() => [
    { x: 0, y: 1, z: phi },
    { x: 0, y: -1, z: phi },
    { x: 0, y: 1, z: -phi },
    { x: 0, y: -1, z: -phi },
    { x: 1, y: phi, z: 0 },
    { x: -1, y: phi, z: 0 },
    { x: 1, y: -phi, z: 0 },
    { x: -1, y: -phi, z: 0 },
    { x: phi, y: 0, z: 1 },
    { x: -phi, y: 0, z: 1 },
    { x: phi, y: 0, z: -1 },
    { x: -phi, y: 0, z: -1 },
  ], [])

  // Icosahedron edges
  const edges: Edge[] = useMemo(() => [
    { from: 0, to: 1 }, { from: 0, to: 4 }, { from: 0, to: 5 }, { from: 0, to: 8 }, { from: 0, to: 9 },
    { from: 1, to: 6 }, { from: 1, to: 7 }, { from: 1, to: 8 }, { from: 1, to: 9 },
    { from: 2, to: 3 }, { from: 2, to: 4 }, { from: 2, to: 5 }, { from: 2, to: 10 }, { from: 2, to: 11 },
    { from: 3, to: 6 }, { from: 3, to: 7 }, { from: 3, to: 10 }, { from: 3, to: 11 },
    { from: 4, to: 5 }, { from: 4, to: 8 }, { from: 4, to: 10 },
    { from: 5, to: 9 }, { from: 5, to: 11 },
    { from: 6, to: 7 }, { from: 6, to: 8 }, { from: 6, to: 10 },
    { from: 7, to: 9 }, { from: 7, to: 11 },
    { from: 8, to: 10 }, { from: 9, to: 11 },
  ], [])

  // Rotation based on time and scroll
  const rotationX = time * 0.5 + scrollProgress * Math.PI * 2
  const rotationY = time * 0.3 + scrollProgress * Math.PI * 1.5
  const rotationZ = time * 0.2 + scrollProgress * Math.PI * 0.5

  // 3D rotation functions
  const rotateX = (p: Point3D, angle: number): Point3D => ({
    x: p.x,
    y: p.y * Math.cos(angle) - p.z * Math.sin(angle),
    z: p.y * Math.sin(angle) + p.z * Math.cos(angle),
  })

  const rotateY = (p: Point3D, angle: number): Point3D => ({
    x: p.x * Math.cos(angle) + p.z * Math.sin(angle),
    y: p.y,
    z: -p.x * Math.sin(angle) + p.z * Math.cos(angle),
  })

  const rotateZ = (p: Point3D, angle: number): Point3D => ({
    x: p.x * Math.cos(angle) - p.y * Math.sin(angle),
    y: p.x * Math.sin(angle) + p.y * Math.cos(angle),
    z: p.z,
  })

  // Apply rotations and project to 2D
  const scale = 120
  const centerX = 250
  const centerY = 280
  
  const transformedVertices = baseVertices.map(v => {
    let p = rotateX(v, rotationX)
    p = rotateY(p, rotationY)
    p = rotateZ(p, rotationZ)
    
    // Perspective projection
    const perspective = 4
    const projectionScale = perspective / (perspective + p.z)
    
    return {
      x: centerX + p.x * scale * projectionScale,
      y: centerY + p.y * scale * projectionScale,
      z: p.z,
      scale: projectionScale,
    }
  })

  // Sort edges by average z depth for proper rendering
  const sortedEdges = [...edges].sort((a, b) => {
    const avgZA = (transformedVertices[a.from].z + transformedVertices[a.to].z) / 2
    const avgZB = (transformedVertices[b.from].z + transformedVertices[b.to].z) / 2
    return avgZA - avgZB
  })

  return (
    <div
      className="absolute right-[-5vw] bottom-[0vh] w-[55vw] h-[85vh] pointer-events-none hidden lg:block"
      style={{
        maskImage: "radial-gradient(ellipse 80% 70% at 60% 55%, black 20%, transparent 70%)",
        WebkitMaskImage: "radial-gradient(ellipse 80% 70% at 60% 55%, black 20%, transparent 70%)",
        transform: `translateY(${scrollProgress * 150}px)`,
        opacity: 1 - scrollProgress * 0.8,
      }}
    >
      <svg viewBox="0 0 500 500" className="w-full h-full">
        {/* Edges - wireframe */}
        {sortedEdges.map((edge, i) => {
          const from = transformedVertices[edge.from]
          const to = transformedVertices[edge.to]
          const avgZ = (from.z + to.z) / 2
          const depth = (avgZ + 2) / 4 // normalize to 0-1
          
          return (
            <line
              key={`edge-${i}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="#C9A96E"
              strokeWidth={1 + depth * 1.5}
              strokeOpacity={0.15 + depth * 0.5}
            />
          )
        })}
        
        {/* Vertices - nodes */}
        {transformedVertices
          .map((v, i) => ({ ...v, index: i }))
          .sort((a, b) => a.z - b.z)
          .map((v) => {
            const depth = (v.z + 2) / 4
            const size = 3 + depth * 5
            
            return (
              <g key={`vertex-${v.index}`}>
                {/* Node */}
                <rect
                  x={v.x - size / 2}
                  y={v.y - size / 2}
                  width={size}
                  height={size}
                  fill="#C9A96E"
                  fillOpacity={0.3 + depth * 0.6}
                />
                {/* Inner glow for closer nodes */}
                {depth > 0.6 && (
                  <rect
                    x={v.x - size / 4}
                    y={v.y - size / 4}
                    width={size / 2}
                    height={size / 2}
                    fill="#F0EEE8"
                    fillOpacity={0.5}
                  />
                )}
              </g>
            )
          })}
      </svg>
    </div>
  )
}
