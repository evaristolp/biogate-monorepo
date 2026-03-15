"use client"

import { useEffect, useRef } from "react"
import * as THREE from "three"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

gsap.registerPlugin(ScrollTrigger)

// ─── Vertex Shader ────────────────────────────────────────────────────────────
// 3D Simplex noise displaces vertices along normals; passes vNoise to fragment
const vertexShader = `
  uniform float uTime;
  varying float vNoise;
  varying vec3 vNormal;

  // — Simplex noise helpers (Stefan Gustavson) —
  vec3 mod289(vec3 x){ return x - floor(x*(1./289.))*289.; }
  vec4 mod289(vec4 x){ return x - floor(x*(1./289.))*289.; }
  vec4 permute(vec4 x){ return mod289(((x*34.)+1.)*x); }
  vec4 taylorInvSqrt(vec4 r){ return 1.79284291400159 - 0.85373472095314*r; }

  float snoise(vec3 v){
    const vec2 C = vec2(1./6., 1./3.);
    const vec4 D = vec4(0.,0.5,1.,2.);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g  = step(x0.yzx, x0.xyz);
    vec3 l  = 1. - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
      i.z + vec4(0.,i1.z,i2.z,1.))
      + i.y + vec4(0.,i1.y,i2.y,1.))
      + i.x + vec4(0.,i1.x,i2.x,1.));
    float n_ = .142857142857;
    vec3  ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.*floor(p*ns.z*ns.z);
    vec4 x_ = floor(j*ns.z);
    vec4 y_ = floor(j - 7.*x_);
    vec4 x = x_*ns.x + ns.yyyy;
    vec4 y = y_*ns.x + ns.yyyy;
    vec4 h = 1. - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0)*2.+1.;
    vec4 s1 = floor(b1)*2.+1.;
    vec4 sh = -step(h, vec4(0.));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(
      dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(.6 - vec4(
      dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.);
    m = m*m;
    return 42.*(dot(m*m, vec4(
      dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3))));
  }

  void main(){
    vec3 pos = position;
    float t   = uTime * 0.38;

    // layered octaves for organic complexity
    float n  = snoise(pos * 0.9  + vec3(t * 0.6,  t * 0.4,  t * 0.3));
    float n2 = snoise(pos * 1.9  + vec3(-t * 0.5, t * 0.7, -t * 0.2)) * 0.5;
    float n3 = snoise(pos * 3.8  + vec3(t * 0.3, -t * 0.6,  t * 0.8)) * 0.25;

    float noise = n + n2 + n3;
    vNoise = noise;
    vNormal = normal;

    // displace along normals
    pos += normal * noise * 0.32;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`

// ─── Fragment Shader ──────────────────────────────────────────────────────────
// Maps vNoise → heatmap gradient: deep indigo → cobalt → gold → ember
const fragmentShader = `
  varying float vNoise;
  varying vec3 vNormal;
  uniform float uTime;

  vec3 heatmap(float t){
    // 4-stop gradient:
    // 0.0 → deep navy  (#0a0f2e)
    // 0.3 → cobalt     (#1a3a8f)
    // 0.6 → gold       (#C9A96E)
    // 1.0 → ember      (#8B1A1A)
    vec3 c0 = vec3(0.039, 0.059, 0.180); // deep navy
    vec3 c1 = vec3(0.102, 0.227, 0.561); // cobalt
    vec3 c2 = vec3(0.788, 0.663, 0.431); // gold (#C9A96E)
    vec3 c3 = vec3(0.545, 0.102, 0.102); // ember

    if(t < 0.333)      return mix(c0, c1, t / 0.333);
    else if(t < 0.666) return mix(c1, c2, (t - 0.333) / 0.333);
    else               return mix(c2, c3, (t - 0.666) / 0.334);
  }

  void main(){
    float n = clamp((vNoise + 1.0) * 0.5, 0.0, 1.0);

    // subtle rim light
    vec3 viewDir = normalize(vec3(0.0, 0.0, 1.0));
    float rim = 1.0 - max(dot(normalize(vNormal), viewDir), 0.0);
    rim = pow(rim, 2.8) * 0.45;

    vec3 color = heatmap(n);
    color += vec3(0.06, 0.05, 0.03) * rim;

    // vignette at edges of the sphere
    float alpha = smoothstep(0.0, 0.18, n) * 0.88 + rim * 0.35;

    gl_FragColor = vec4(color, alpha);
  }
`

export function HeatmapMesh() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    // ─── Renderer ─────────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setClearColor(0x000000, 0)

    // ─── Scene / Camera ───────────────────────────────────────────────────────
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    )
    camera.position.set(0, 0, 5)

    // ─── Mesh ─────────────────────────────────────────────────────────────────
    const geometry = new THREE.IcosahedronGeometry(1.6, 128)
    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
      },
      transparent: true,
      depthWrite: false,
      side: THREE.FrontSide,
    })
    const mesh = new THREE.Mesh(geometry, material)
    // start off-screen right, slightly above center
    mesh.position.set(2.2, 0.4, 0)
    scene.add(mesh)

    // ─── GSAP ScrollTrigger ───────────────────────────────────────────────────
    // The mesh drifts through viewport space as the user scrolls.
    // uTime drives the organic liquid movement independently.
    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: document.body,
        start: "top top",
        end: "bottom bottom",
        scrub: 1.4,
      },
    })

    tl.to(mesh.position, { x: -1.8, y: -0.6, z: -0.5, ease: "none" }, 0)
    tl.to(mesh.rotation, { x: Math.PI * 0.6, y: Math.PI * 1.1, ease: "none" }, 0)
    tl.to(mesh.position, { x: 0.8, y: 0.3, z: 0.4, ease: "none" }, 0.5)

    // ─── Animation loop ───────────────────────────────────────────────────────
    let animId: number
    const clock = new THREE.Clock()

    function animate() {
      animId = requestAnimationFrame(animate)
      material.uniforms.uTime.value = clock.getElapsedTime()
      mesh.rotation.y += 0.0018
      mesh.rotation.x += 0.0007
      renderer.render(scene, camera)
    }
    animate()

    // ─── Resize ───────────────────────────────────────────────────────────────
    function onResize() {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener("resize", onResize)

    return () => {
      cancelAnimationFrame(animId)
      ScrollTrigger.getAll().forEach((st) => st.kill())
      window.removeEventListener("resize", onResize)
      renderer.dispose()
      geometry.dispose()
      material.dispose()
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden
    />
  )
}
