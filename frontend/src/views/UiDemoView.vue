<!--
  /_ui — design system playground. Dev-only. Shows primitives in several
  variants so we can iterate the studio look without touching real views.
  Route is gated with `import.meta.env.DEV`.
-->
<script setup lang="ts">
import { ref } from 'vue'
import Knob from '@/ui/primitives/Knob.vue'
import Fader from '@/ui/primitives/Fader.vue'
import PixelMeter from '@/ui/primitives/PixelMeter.vue'
import LED from '@/ui/primitives/LED.vue'

const stability = ref(0.5)
const similarity = ref(0.85)
const style = ref(0.15)
const gainDb = ref(-6)
const masterFader = ref(0.72)
const hiShelf = ref(0.4)
const loShelf = ref(0.55)
</script>

<template>
  <div class="demo-root">
    <header class="demo-header">
      <div class="demo-brand">
        <span class="demo-brand__mark" aria-hidden="true">■</span>
        <span>voice cloning · design system</span>
      </div>
      <nav class="demo-nav">
        <a href="#tokens">TOKENS</a>
        <a href="#type">TYPOGRAPHY</a>
        <a href="#knobs">KNOBS</a>
        <a href="#faders">FADERS</a>
        <a href="#meters">METERS</a>
        <a href="#leds">LEDS</a>
      </nav>
    </header>

    <main class="demo-main">
      <section class="demo-hero">
        <h1 class="display-1">STUDIO SYSTEM</h1>
        <p class="demo-hero__lede">
          Tokens, tipografía y primitives del rediseño UI. Esta pantalla es
          dev-only y existe para validar estética antes de cablearla a las
          vistas reales.
        </p>
      </section>

      <section id="tokens" class="demo-section">
        <h2 class="demo-section__title">01 · Surfaces &amp; Palette</h2>
        <div class="demo-swatches">
          <div class="sw" style="--c: var(--bg-0)"><span>bg-0</span><code>#0a0a0c</code></div>
          <div class="sw" style="--c: var(--bg-1)"><span>bg-1</span><code>#111114</code></div>
          <div class="sw" style="--c: var(--bg-2)"><span>bg-2</span><code>#17171c</code></div>
          <div class="sw" style="--c: var(--bg-3)"><span>bg-3</span><code>#1f1f26</code></div>
          <div class="sw" style="--c: var(--accent)"><span>accent</span><code>#7c5cff</code></div>
          <div class="sw" style="--c: var(--accent-glow)"><span>glow</span><code>#a88aff</code></div>
          <div class="sw" style="--c: var(--signal-green)"><span>green</span><code>#00e5a0</code></div>
          <div class="sw" style="--c: var(--signal-amber)"><span>amber</span><code>#ffb020</code></div>
          <div class="sw" style="--c: var(--signal-red)"><span>red</span><code>#ff3b5c</code></div>
          <div class="sw" style="--c: var(--signal-blue)"><span>blue</span><code>#38bdf8</code></div>
        </div>
      </section>

      <section id="type" class="demo-section">
        <h2 class="demo-section__title">02 · Typography</h2>
        <div class="demo-type studio-card">
          <div class="display-1">Display / 56 px</div>
          <div class="display-2">Headline / 40 px</div>
          <div style="font-size:24px; font-weight:500;">Title · Inter Tight 500 / 24</div>
          <div style="font-size:16px;">Body · Inter Tight 400 / 16. Castellano técnico: síntesis zero-shot, watermarking AudioSeal, puntuación AASIST.</div>
          <div class="studio-label">ALL CAPS MONO · JetBrains 500 / 11</div>
          <div class="studio-value" style="font-size:14px;">TIMECODE · 00:00:23.145 · -6.2 dB · 2026-04-14T20:11:02Z</div>
        </div>
      </section>

      <section id="knobs" class="demo-section">
        <h2 class="demo-section__title">03 · Knobs</h2>
        <div class="demo-card studio-card">
          <div class="demo-group">
            <Knob v-model="stability" :min="0" :max="1" :step="0.01" :default="0.5"
                  label="STABILITY" unit="" :size="64" :precision="2" />
            <Knob v-model="similarity" :min="0" :max="1" :step="0.01" :default="0.85"
                  label="SIMILARITY" :size="64" :precision="2" />
            <Knob v-model="style" :min="0" :max="1" :step="0.01" :default="0"
                  label="STYLE" :size="64" :precision="2" />
            <Knob v-model="gainDb" :min="-24" :max="12" :step="0.5" :default="0"
                  label="GAIN" unit="dB" :size="48" :precision="1" />
            <Knob v-model="hiShelf" :min="0" :max="1" :step="0.01" :default="0.5"
                  label="HIGH" :size="32" :precision="2" />
            <Knob v-model="loShelf" :min="0" :max="1" :step="0.01" :default="0.5"
                  label="LOW" :size="32" :precision="2" />
            <Knob :model-value="0.5" :min="0" :max="1" label="DISABLED" :size="48" disabled />
          </div>
          <p class="demo-note">
            Drag vertical · Shift = fine · Doble-clic = reset · Flechas / PgUp
            / PgDn / Home / End · Rueda con modifier Shift.
          </p>
        </div>
      </section>

      <section id="faders" class="demo-section">
        <h2 class="demo-section__title">04 · Faders</h2>
        <div class="demo-card studio-card">
          <div class="demo-group" style="gap:48px; align-items:flex-end;">
            <Fader v-model="masterFader" :min="0" :max="1" :step="0.01" :default="0.75"
                   label="MASTER" :height="200" :precision="2" />
            <Fader v-model="gainDb" :min="-24" :max="12" :step="0.5" :default="0"
                   label="CH 1" unit="dB" :height="140" :precision="1" />
            <Fader v-model="similarity" :min="0" :max="1" :step="0.01" :default="0.85"
                   label="CH 2" :height="140" :precision="2" />
            <Fader :model-value="0.3" :min="0" :max="1" label="DISABLED" :height="140" disabled />
          </div>
        </div>
      </section>

      <section id="meters" class="demo-section">
        <h2 class="demo-section__title">05 · Pixel Meters</h2>
        <div class="demo-card studio-card" style="gap:24px;">
          <PixelMeter label="MASTER L" demo :width="640" :height="56" :cells="40" :rows="6" />
          <PixelMeter label="MASTER R" demo :width="640" :height="56" :cells="40" :rows="6" />
          <div style="display:flex; gap:24px; align-items:flex-end;">
            <PixelMeter orientation="vertical" label="CH 1" demo
                        :width="44" :height="200" :cells="24" :rows="3" />
            <PixelMeter orientation="vertical" label="CH 2" demo
                        :width="44" :height="200" :cells="24" :rows="3" />
            <PixelMeter orientation="vertical" label="CH 3" demo
                        :width="44" :height="200" :cells="24" :rows="3" />
            <PixelMeter orientation="vertical" label="CH 4" demo
                        :width="44" :height="200" :cells="24" :rows="3" />
          </div>
          <p class="demo-note">
            Escala log -60 / +3 dB · peak hold decay 12 dB/s · 60 fps canvas.
            El modo demo anima RMS y peak con dos senos; en producción se
            alimenta desde `useMeter()` con AnalyserNode real.
          </p>
        </div>
      </section>

      <section id="leds" class="demo-section">
        <h2 class="demo-section__title">06 · LEDs</h2>
        <div class="demo-card studio-card">
          <div class="demo-group" style="gap:24px;">
            <LED color="green" label="READY" />
            <LED color="amber" label="WARN" />
            <LED color="red" label="CLIP" pulse />
            <LED color="blue" label="INFO" />
            <LED color="accent" label="LINK" />
            <LED :on="false" label="OFF" />
            <LED color="red" label="REC" pulse size="md" />
          </div>
        </div>
      </section>

      <footer class="demo-footer studio-value">
        <span>STUDIO SYSTEM · v0.1 · dark</span>
        <span>built with Vue 3 · Tailwind 4 · CSS vars</span>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.demo-root {
  min-height: 100vh;
  background:
    radial-gradient(1200px 600px at 20% -10%, color-mix(in srgb, var(--accent) 12%, transparent), transparent 60%),
    var(--bg-0);
  color: var(--fg-0);
}

.demo-header {
  position: sticky;
  top: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 32px;
  background: color-mix(in srgb, var(--bg-0) 80%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
  z-index: 10;
}
.demo-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-0);
}
.demo-brand__mark {
  color: var(--accent);
  text-shadow: 0 0 12px var(--accent);
}
.demo-nav {
  display: flex;
  gap: 18px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
}
.demo-nav a {
  color: var(--fg-1);
  text-decoration: none;
  padding: 4px 6px;
  border-radius: var(--radius-2);
  transition: color var(--dur-base) var(--ease-studio),
              background var(--dur-base) var(--ease-studio);
}
.demo-nav a:hover { color: var(--fg-0); background: var(--bg-2); }

.demo-main {
  max-width: 1280px;
  margin: 0 auto;
  padding: 48px 32px 120px;
  display: flex;
  flex-direction: column;
  gap: 72px;
}

.demo-hero {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-top: 40px;
}
.demo-hero__lede {
  max-width: 620px;
  color: var(--fg-1);
  font-size: 18px;
  line-height: 1.5;
}

.demo-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.demo-section__title {
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--fg-2);
}

.demo-swatches {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}
.sw {
  position: relative;
  height: 92px;
  border-radius: var(--radius-4);
  border: 1px solid var(--line);
  background: var(--c);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  box-shadow: var(--shadow-card);
}
.sw span {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #fff;
  mix-blend-mode: difference;
}
.sw code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #fff;
  mix-blend-mode: difference;
  opacity: 0.8;
}

.demo-type {
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.demo-card {
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.demo-group {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  align-items: center;
}
.demo-note {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-2);
  letter-spacing: 0.04em;
}

.demo-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 24px;
  border-top: 1px solid var(--line);
  color: var(--fg-2);
  font-variant-numeric: tabular-nums;
}
</style>
