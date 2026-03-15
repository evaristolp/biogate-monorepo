"use client"

import { useEffect, useRef } from "react"
import * as THREE from "three"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

gsap.registerPlugin(ScrollTrigger)

// ─── Vertex Shader ────────────────────────────────────────────────────────────
// Plane of dots — simplex noise ripples through z-axis like fabric in wind
const vertexShader = `
  uniform float uTime;
  uniform float uScroll;   // 0 → 1 progress through hero
  varying float vDepth;

  vec3 mod289(vec3 x){ return x - floor(x*(1./289.))*289.; }
  vec4 mod289(vec4 x){ return x - floor(x*(1./289.))*289.; }
  vec4 permute(vec4 x){ return mod289(((x*34.)+1.)*x); }
  vec4 taylorInvSqrt(vec4 r){ return 1.79284291400159 - 0.85373472095314*r; }

  float snoise(vec3 v){
    const vec2 C = vec2(1./6.,1./3.);
    const vec4 D = vec4(0.,0.5,1.,2.);
    vec3 i  = floor(v+dot(v,C.yyy));
    vec3 x0 = v-i+dot(i,C.xxx);
    vec3 g  = step(x0.yzx,x0.xyz);
    vec3 l  = 1.-g;
    vec3 i1 = min(g.xyz,l.zxy);
    vec3 i2 = max(g.xyz,l.zxy);
    vec3 x1 = x0-i1+C.xxx;
    vec3 x2 = x0-i2+C.yyy;
    vec3 x3 = x0-D.yyy;
    i = mod289(i);
    vec4 p = permute(permute(permute(
      i.z+vec4(0.,i1.z,i2.z,1.))
      +i.y+vec4(0.,i1.y,i2.y,1.))
      +i.x+vec4(0.,i1.x,i2.x,1.));
    float n_ = .142857142857;
    vec3 ns = n_*D.wyz-D.xzx;
    vec4 j = p-49.*floor(p*ns.z*ns.z);
    vec4 x_ = floor(j*ns.z);
    vec4 y_ = floor(j-7.*x_);
    vec4 x = x_*ns.x+ns.yyyy;
    vec4 y = y_*ns.x+ns.yyyy;
    vec4 h = 1.-abs(x)-abs(y);
    vec4 b0 = vec4(x.xy,y.xy);
    vec4 b1 = vec4(x.zw,y.zw);
    vec4 s0 = floor(b0)*2.+1.;
    vec4 s1 = floor(b1)*2.+1.;
    vec4 sh = -step(h,vec4(0.));
    vec4 a0 = b0.xzyw+s0.xzyw*sh.xxyy;
    vec4 a1 = b1.xzyw+s1.xzyw*sh.zzww;
    vec3 p0 = vec3(a0.xy,h.x);
    vec3 p1 = vec3(a0.zw,h.y);
    vec3 p2 = vec3(a1.xy,h.z);
    vec3 p3 = vec3(a1.zw,h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.);
    m = m*m;
    return 42.*(dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3))));
  }

  void main(){
    vec3 pos = position;
    float t = uTime * 0.5;

    // fabric ripple — multi-octave z displacement
    float wave  = snoise(vec3(pos.x * 0.6, pos.y * 0.6, t * 0.7))          * 0.55;
    float wave2 = snoise(vec3(pos.x * 1.4 + 1.3, pos.y * 1.4 - 0.9, t * 0.4)) * 0.25;
    float wave3 = snoise(vec3(pos.x * 3.1 - 2.2, pos.y * 3.1 + 1.7, t * 1.1)) * 0.10;

    pos.z += wave + wave2 + wave3;

    // tilt the plane on scroll (spin forward into viewer)
    float tilt = uScroll * 3.14159 * 0.55;
    float cosT = cos(tilt);
    float sinT = sin(tilt);
    float newY = pos.y * cosT - pos.z * sinT;
    float newZ = pos.y * sinT + pos.z * cosT;
    pos.y = newY;
    pos.z = newZ;

    vDepth = (wave + wave2 + wave3 + 1.0) * 0.5;

    gl_PointSize = mix(1.2, 2.8, vDepth) * (1.0 - uScroll * 0.5);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`

// ─── Fragment Shader ──────────────────────────────────────────────────────────
// Crisp white dots, fade toward edges of each point
const fragmentShader = `
  varying float vDepth;
  uniform float uScroll;

  void main(){
    // round dot shape
    vec2 coord = gl_PointCoord - 0.5;
    float dist = length(coord);
    if(dist > 0.5) discard;

    // soft edge
    float alpha = smoothstep(0.5, 0.15, dist);

    // depth-based brightness — foreground dots slightly brighter
    float brightness = mix(0.35, 1.0, vDepth);

    // fade out as scroll approaches 1
    float fadeOut = 1.0 - smoothstep(0.7, 1.0, uScroll);

    gl_FragColor = vec4(vec3(brightness), alpha * fadeOut * 0.85);
  }
`

export function HeatmapMesh() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    // ─── Renderer ─────────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setClearColor(0x000000, 0)

    // ─── Scene / Camera ───────────────────────────────────────────────────────
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 100)
    camera.position.set(0, 0, 4.5)

    // ─── Geometry: subdivided plane rendered as Points ─────────────────────────
    const segments = 180
    const geometry = new THREE.PlaneGeometry(7, 7, segments, segments)
    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime:   { value: 0 },
        uScroll: { value: 0 },
      },
      transparent: true,
      depthWrite: false,
    })

    const mesh = new THREE.Points(geometry, material)
    // slight tilt to look like a draped fabric at rest
    mesh.rotation.x = -0.18
    scene.add(mesh)

    // ─── Scroll uniform update ─────────────────────────────────────────────────
    // hero height = 100vh; scroll 0 → heroBottom maps uScroll 0 → 1
    const scrollProxy = { value: 0 }
    let heroHeight = window.innerHeight

    ScrollTrigger.create({
      trigger: "#hero",
      start: "top top",
      end: "bottom top",
      scrub: true,
      onUpdate: (self) => {
        scrollProxy.value = self.progress
        material.uniforms.uScroll.value = self.progress
      },
    })

    // ─── Canvas visibility ─────────────────────────────────────────────────────
    // Hide canvas once user is fully past the hero so it doesn't render offscreen
    ScrollTrigger.create({
      trigger: "#hero",
      start: "bottom top",
      onEnter: () => { canvas.style.display = "none" },
      onLeaveBack: () => { canvas.style.display = "block" },
    })

    // ─── Resize ───────────────────────────────────────────────────────────────
    function onResize() {
      heroHeight = window.innerHeight
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }
    window.addEventListener("resize", onResize)

    // ─── Animation loop ───────────────────────────────────────────────────────
    let animId: number
    const clock = new THREE.Clock()

    function animate() {
      animId = requestAnimationFrame(animate)
      material.uniforms.uTime.value = clock.getElapsedTime()
      renderer.render(scene, camera)
    }
    animate()

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
