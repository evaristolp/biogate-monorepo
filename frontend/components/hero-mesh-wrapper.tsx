"use client"

import dynamic from "next/dynamic"

const HeroMesh = dynamic(
  () => import("@/components/hero-mesh").then((mod) => mod.HeroMesh),
  { ssr: false }
)

export function HeroMeshWrapper() {
  return <HeroMesh />
}
