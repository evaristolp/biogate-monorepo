# v0 Prompt: Fix mobile jitter on the hero network animation

Copy the prompt below into v0 when the **mobile** version of the site has jittery or stuttery animation (e.g. the network/graph canvas on the hero section). Try **one approach at a time**; if the first doesn’t fix it, try the next.

---

## Prompt for v0 (Approach A – containment and compositing)

**Task:** Remove jitter/stutter on mobile during the hero section animation (the full-screen network canvas behind the hero).

**Constraints:** Keep the same visual design and desktop behavior. Change only what’s needed for mobile performance.

**Implement this approach:**

1. **Containment**  
   On the hero section wrapper (the container that holds the canvas/network visual):
   - Add `contain: layout paint` (e.g. via Tailwind `contain-layout` and `contain-paint`, or a custom class).
   - Optionally add `content-visibility: auto` so the browser can skip work when the section is off-screen.

2. **Compositing**  
   On the canvas (or its immediate wrapper):
   - Ensure it stays on its own layer: e.g. `transform: translateZ(0)` or `will-change: transform` (only on the canvas wrapper, not on many elements).
   - Add `backface-visibility: hidden` to reduce subpixel flicker.

3. **Scroll**  
   Ensure the hero section doesn’t trigger layout or paint during scroll (the containment and compositing above should help). If the canvas already pauses when off-screen or during scroll, keep that behavior.

**Acceptance:** On mobile (or Chrome DevTools mobile emulation), scroll the page and watch the hero; the animation should not visibly jitter or stutter during scroll or when the hero is in view.

---

## Prompt for v0 (Approach B – simplify animation on mobile)

**Task:** Remove jitter/stutter on mobile during the hero section animation by simplifying the animation on small/touch screens.

**Constraints:** Desktop keeps the current rich animation. Only mobile (e.g. `max-width: 768px` or `pointer: coarse`) should be simplified.

**Implement this approach:**

1. **Detect mobile**  
   Use a media query or `window.matchMedia('(max-width: 768px)')` / `(pointer: coarse)` so the same component can render differently on mobile.

2. **Mobile: reduce motion or use a static fallback**  
   Pick one (or combine):
   - **Option 1:** On mobile, don’t run the canvas animation at all; show a static gradient or a single blurred/soft image that matches the hero look.
   - **Option 2:** On mobile, run the canvas at a much lower update rate (e.g. one frame every 200–300 ms) so it’s a slow drift instead of smooth 60fps, reducing CPU/GPU load and jitter.
   - **Option 3:** On mobile, replace the canvas with a pure CSS animation (e.g. slow-moving gradients or a few floating blurs) so the browser can optimize and composite without JavaScript-driven canvas repaints.

3. **No layout thrash**  
   Ensure the hero container has a fixed height (e.g. `min-h-dvh` or `min-h-screen`) and that the canvas or its wrapper doesn’t change size during the animation.

**Acceptance:** On mobile, the hero section looks good and no longer jitters; desktop behavior is unchanged.

---

## Prompt for v0 (Approach C – fixed timestep and offscreen canvas)

**Task:** Fix mobile jitter in the hero network animation by making the animation loop more predictable and, on mobile, drawing to an offscreen canvas then blitting to the visible one.

**Constraints:** Keep the same visual; only change how the canvas is updated.

**Implement this approach:**

1. **Fixed timestep**  
   Drive the animation with a fixed delta (e.g. 1/60 s). Use `requestAnimationFrame` only to schedule frames, but advance simulation time by a constant step. This avoids speed-up/slow-down and reduces jitter when the main thread is busy.

2. **Double buffering on mobile**  
   On mobile (matchMedia or similar):
   - Create an offscreen canvas with the same logical size (and same `devicePixelRatio` as the on-screen canvas).
   - Each frame: draw the full scene to the offscreen canvas, then in one draw call copy it to the on-screen canvas (e.g. `drawImage(offscreenCanvas, 0, 0)`). This can reduce flicker and layout-related jitter.

3. **Single repaint per frame**  
   Ensure the canvas is only updated once per animation frame (no mid-frame resizes or style changes that force reflow). Keep the canvas size in sync with its container only on resize, not every frame.

**Acceptance:** On mobile, the hero animation runs smoothly without visible jitter; desktop behavior is unchanged.

---

## Prompt for v0 (Approach D – CSS-only hero on mobile)

**Task:** Eliminate mobile jitter by removing the JavaScript canvas animation on mobile and using a CSS-only hero background.

**Constraints:** Desktop keeps the current interactive network canvas. Mobile (e.g. `max-width: 768px` or touch device) must show a non-jittery hero.

**Implement this approach:**

1. **Conditional render**  
   Do not render the heavy network canvas at all on mobile. Use a media query or `useEffect` + `window.matchMedia` so the canvas component is only mounted on desktop.

2. **CSS hero background for mobile**  
   On mobile, the hero should use only:
   - Layered radial gradients (already present in the layout) and/or
   - A very subtle CSS animation (e.g. `@keyframes` on `background-position` or `opacity` with long duration and low contrast) so the background feels alive without canvas or complex JS.

3. **Same overall look**  
   Colors and general feel should match the current hero (dark blue, soft blue/cyan/purple blobs). No canvas, no node/line drawing on mobile.

**Acceptance:** On mobile, the hero has no jitter and no canvas; on desktop, the existing network animation is unchanged.

---

## How to use these prompts

- Start with **Approach A** (containment + compositing). It’s the least invasive.
- If jitter remains, try **Approach B** (simplify on mobile) or **Approach D** (CSS-only on mobile).
- If you must keep the full canvas on mobile, try **Approach C** (fixed timestep + offscreen canvas).

Use a single approach per v0 run; combine only if one approach alone wasn’t enough and you’ve verified the previous change didn’t regress desktop.
