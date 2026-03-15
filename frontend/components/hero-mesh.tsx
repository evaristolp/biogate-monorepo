"use client"

import { useRef, useMemo, useEffect, useState } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import * as THREE from "three"

interface NodeData {
  position: THREE.Vector3
  connections: number[]
  velocity: THREE.Vector3
}

function NetworkMesh({ scrollProgress }: { scrollProgress: number }) {
  const groupRef = useRef<THREE.Group>(null)
  const pointsRef = useRef<THREE.Points>(null)
  const linesRef = useRef<THREE.LineSegments>(null)
  
  // Generate network nodes
  const { nodes, positions, linePositions, colors } = useMemo(() => {
    const nodeCount = 60
    const nodes: NodeData[] = []
    const positions: number[] = []
    const colors: number[] = []
    
    // Create nodes in a spherical distribution
    for (let i = 0; i < nodeCount; i++) {
      const phi = Math.acos(-1 + (2 * i) / nodeCount)
      const theta = Math.sqrt(nodeCount * Math.PI) * phi
      
      const radius = 2.2 + Math.random() * 0.8
      const x = radius * Math.cos(theta) * Math.sin(phi)
      const y = radius * Math.sin(theta) * Math.sin(phi)
      const z = radius * Math.cos(phi)
      
      nodes.push({
        position: new THREE.Vector3(x, y, z),
        connections: [],
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 0.002,
          (Math.random() - 0.5) * 0.002,
          (Math.random() - 0.5) * 0.002
        ),
      })
      
      positions.push(x, y, z)
      
      // Gold color with variation
      const intensity = 0.4 + Math.random() * 0.6
      colors.push(0.788 * intensity, 0.663 * intensity, 0.431 * intensity)
    }
    
    // Create connections between nearby nodes
    const linePositions: number[] = []
    const maxDistance = 1.8
    
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const distance = nodes[i].position.distanceTo(nodes[j].position)
        if (distance < maxDistance) {
          nodes[i].connections.push(j)
          linePositions.push(
            nodes[i].position.x, nodes[i].position.y, nodes[i].position.z,
            nodes[j].position.x, nodes[j].position.y, nodes[j].position.z
          )
        }
      }
    }
    
    return { nodes, positions, linePositions, colors }
  }, [])
  
  // Animate
  useFrame((state) => {
    if (!groupRef.current) return
    
    const time = state.clock.elapsedTime
    
    // Slow rotation
    groupRef.current.rotation.y = time * 0.05 + scrollProgress * 2
    groupRef.current.rotation.x = Math.sin(time * 0.03) * 0.15 + scrollProgress * 0.5
    
    // Subtle breathing scale
    const scale = 1 + Math.sin(time * 0.5) * 0.03
    groupRef.current.scale.setScalar(scale)
    
    // Move based on scroll
    groupRef.current.position.y = -scrollProgress * 3
    groupRef.current.position.z = -scrollProgress * 2
  })
  
  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Network nodes */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array(positions), 3]}
          />
          <bufferAttribute
            attach="attributes-color"
            args={[new Float32Array(colors), 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          size={0.08}
          vertexColors
          transparent
          opacity={0.9}
          sizeAttenuation
        />
      </points>
      
      {/* Connection lines */}
      <lineSegments ref={linesRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[new Float32Array(linePositions), 3]}
          />
        </bufferGeometry>
        <lineBasicMaterial
          color="#C9A96E"
          transparent
          opacity={0.15}
        />
      </lineSegments>
      
      {/* Core glow sphere */}
      <mesh>
        <icosahedronGeometry args={[0.6, 2]} />
        <meshBasicMaterial
          color="#C9A96E"
          transparent
          opacity={0.08}
          wireframe
        />
      </mesh>
      
      {/* Outer shell */}
      <mesh>
        <icosahedronGeometry args={[3.2, 1]} />
        <meshBasicMaterial
          color="#C9A96E"
          transparent
          opacity={0.03}
          wireframe
        />
      </mesh>
    </group>
  )
}

export function HeroMesh() {
  const [scrollProgress, setScrollProgress] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  
  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY
      const windowHeight = window.innerHeight
      // Progress from 0 to 1 over the first viewport height
      const progress = Math.min(scrollY / windowHeight, 1)
      setScrollProgress(progress)
    }
    
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])
  
  return (
    <div
      ref={containerRef}
      className="absolute right-0 top-1/2 -translate-y-1/2 w-[50vw] h-[80vh] pointer-events-none hidden lg:block"
      style={{
        maskImage: "radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 70%)",
        WebkitMaskImage: "radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 70%)",
      }}
    >
      <Canvas
        camera={{ position: [0, 0, 7], fov: 45 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
      >
        <NetworkMesh scrollProgress={scrollProgress} />
      </Canvas>
    </div>
  )
}
