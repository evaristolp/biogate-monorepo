"use client"

import dynamic from "next/dynamic"

const HeatmapMesh = dynamic(
  () => import("./heatmap-mesh").then((m) => ({ default: m.HeatmapMesh })),
  { ssr: false }
)

export function HeatmapMeshLoader() {
  return <HeatmapMesh />
}
