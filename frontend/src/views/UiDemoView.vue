<!--
  /_ui — design system playground. Dev-only. Shows primitives + composites
  in several variants so we can iterate the studio look without touching
  real views. Route is gated by `import.meta.env.DEV` in the router.
-->
<script setup lang="ts">
import { ref } from 'vue'
import Knob from '@/ui/primitives/Knob.vue'
import Fader from '@/ui/primitives/Fader.vue'
import PixelMeter from '@/ui/primitives/PixelMeter.vue'
import LED from '@/ui/primitives/LED.vue'
import Switch from '@/ui/primitives/Switch.vue'
import SegmentedDisplay from '@/ui/primitives/SegmentedDisplay.vue'
import SpectrumAnalyzer from '@/ui/primitives/SpectrumAnalyzer.vue'
import WaveformTimeline from '@/ui/primitives/WaveformTimeline.vue'

import InputChannel from '@/ui/composites/InputChannel.vue'
import TransportBar from '@/ui/composites/TransportBar.vue'
import ModelCard from '@/ui/composites/ModelCard.vue'
import JobMonitor from '@/ui/composites/JobMonitor.vue'
import OptionsPanel, { type ElevenOptions } from '@/ui/composites/OptionsPanel.vue'
import RecorderStudio from '@/ui/composites/RecorderStudio.vue'

const stability = ref(0.5)
const similarity = ref(0.85)
const style = ref(0.15)
const gainDb = ref(-6)
const masterFader = ref(0.72)
const hiShelf = ref(0.4)
const loShelf = ref(0.55)
const switchOn = ref(true)

const monitor = ref(0.7)

const selectedModel = ref('chatterbox')
const modelList = [
  { name: 'chatterbox', license: 'MIT', notes: 'default · PerTh nativo',
    cloud: false, clinicalSafe: true, metrics: [
      { label: 'RTF', value: '0.49' }, { label: 'MOS', value: '3.59' }, { label: 'SIM', value: '0.71' },
    ] },
  { name: 'omnivoice', license: 'Apache-2.0', notes: 'mejor similitud · AudioSeal post-hoc',
    cloud: false, clinicalSafe: true, metrics: [
      { label: 'RTF', value: '0.71' }, { label: 'MOS', value: '3.45' }, { label: 'SIM', value: '0.79' },
    ] },
  { name: 'elevenlabs', license: 'proprietary', notes: '🌐 Cloud · NO APTO para datos clínicos',
    cloud: true, clinicalSafe: false, metrics: [
      { label: 'RTF', value: '—' }, { label: 'MOS', value: '—' }, { label: 'SIM', value: '—' },
    ] },
]

const optsOpen = ref(true)
const opts = ref<ElevenOptions>({
  model_id: 'eleven_multilingual_v2',
  stability: 0.5,
  similarity_boost: 0.85,
  style: 0,
  use_speaker_boost: true,
})

const jobPct = ref(42)
const jobRunning = ref(true)
const jobLatency = ref(180)
setInterval(() => {
  if (!jobRunning.value) return
  jobPct.value = (jobPct.value + 2) % 100
  jobLatency.value = 80 + Math.random() * 220
}, 500)
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
        <a href="#type">TYPE</a>
        <a href="#primitives">PRIMITIVES</a>
        <a href="#composites">COMPOSITES</a>
        <a href="#recorder">RECORDER</a>
      </nav>
    </header>

    <main class="demo-main">
      <section class="demo-hero">
        <h1 class="display-1">STUDIO SYSTEM</h1>
        <p class="demo-hero__lede">
          Tokens, tipografía, primitives y composites del rediseño. Esta
          pantalla es dev-only y existe para validar estética antes de
          cablearla a las vistas reales.
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

      <section id="primitives" class="demo-section">
        <h2 class="demo-section__title">03 · Primitives</h2>

        <div class="demo-card studio-card">
          <div class="studio-label">KNOBS (270° · drag · shift=fine · dblclick=reset)</div>
          <div class="demo-group">
            <Knob v-model="stability" :min="0" :max="1" :step="0.01" :default="0.5"
                  label="STABILITY" :size="64" :precision="2" />
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
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">FADERS</div>
          <div class="demo-group" style="gap:48px; align-items:flex-end;">
            <Fader v-model="masterFader" :min="0" :max="1" :step="0.01" :default="0.75"
                   label="MASTER" :height="200" :precision="2" />
            <Fader v-model="gainDb" :min="-24" :max="12" :step="0.5" :default="0"
                   label="CH 1" unit="dB" :height="140" :precision="1" />
            <Fader :model-value="0.3" :min="0" :max="1" label="DISABLED" :height="140" disabled />
          </div>
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">PIXEL METERS · 48×5 densidad acordada · 60 fps</div>
          <PixelMeter label="MASTER L" demo :width="640" :height="56" />
          <PixelMeter label="MASTER R" demo :width="640" :height="56" />
          <div style="display:flex; gap:24px; align-items:flex-end; margin-top:12px;">
            <PixelMeter orientation="vertical" label="CH 1" demo :width="44" :height="200" :cells="30" :rows="3" />
            <PixelMeter orientation="vertical" label="CH 2" demo :width="44" :height="200" :cells="30" :rows="3" />
            <PixelMeter orientation="vertical" label="CH 3" demo :width="44" :height="200" :cells="30" :rows="3" />
            <PixelMeter orientation="vertical" label="CH 4" demo :width="44" :height="200" :cells="30" :rows="3" />
          </div>
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">LEDS · SWITCHES · SEGMENTED DISPLAYS</div>
          <div class="demo-group" style="gap:24px;">
            <LED color="green" label="READY" />
            <LED color="amber" label="WARN" />
            <LED color="red" label="CLIP" pulse />
            <LED color="blue" label="INFO" />
            <LED color="accent" label="LINK" />
            <LED :on="false" label="OFF" />
            <LED color="red" label="REC" pulse size="md" />
          </div>
          <div class="demo-group" style="gap:24px; margin-top:8px;">
            <Switch v-model="switchOn" label="SPEAKER BOOST" />
            <Switch :model-value="false" label="MUTED" />
            <Switch :model-value="true" label="DISABLED" disabled />
          </div>
          <div class="demo-group" style="gap:16px; margin-top:8px;">
            <SegmentedDisplay text="00:00:23.145" tint="green" size="lg" label="TIMECODE" />
            <SegmentedDisplay text="-6.2 dB" tint="amber" size="md" label="PEAK" />
            <SegmentedDisplay text="SYNTHESIZING" tint="green" size="md" blink label="STATUS" />
            <SegmentedDisplay text="AASIST 0.31" tint="blue" size="sm" label="SCORE" />
          </div>
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">SPECTRUM ANALYZER (sin input · placeholder)</div>
          <SpectrumAnalyzer :analyser="null" :height="220" :width="920" />
          <p class="demo-note">
            En <code>RecorderStudio</code> se conecta al <code>AnalyserNode</code> del
            <code>useRecorder</code> y muestra la entrada real. Sin input, sólo se
            pinta el fondo con rejilla.
          </p>
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">WAVEFORM TIMELINE</div>
          <WaveformTimeline :src="null" :height="96" />
          <p class="demo-note">
            Recibe Blob o URL. En RecorderStudio usamos thumbnails canvas ligeros
            por take; en SynthesizeView usaremos este componente completo.
          </p>
        </div>
      </section>

      <section id="composites" class="demo-section">
        <h2 class="demo-section__title">04 · Composites</h2>

        <div class="demo-card studio-card">
          <div class="studio-label">INPUT CHANNELS (mixer strip)</div>
          <div class="demo-group" style="align-items:flex-start;">
            <InputChannel name="MIC / INT" demo-meter />
            <InputChannel name="MIC / EXT" demo-meter />
            <InputChannel name="FILE" demo-meter />
            <InputChannel name="AUX" demo-meter />
          </div>
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">TRANSPORT BAR</div>
          <TransportBar :monitor="monitor" meter-demo @update:monitor="monitor = $event" />
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">MODEL CARDS</div>
          <div class="demo-models">
            <ModelCard
              v-for="m in modelList"
              :key="m.name"
              :name="m.name"
              :license="m.license"
              :notes="m.notes"
              :cloud="m.cloud"
              :clinical-safe="m.clinicalSafe"
              :metrics="m.metrics"
              :selected="selectedModel === m.name"
              @select="selectedModel = m.name"
            />
          </div>
        </div>

        <div class="demo-card studio-card">
          <div class="studio-label">OPTIONS PANEL · JOB MONITOR</div>
          <div class="demo-side-by-side">
            <OptionsPanel v-model:open="optsOpen" v-model:options="opts" />
            <JobMonitor
              :pct="jobPct"
              stage="synthesizing"
              message="aplicando watermark audioseal"
              :running="jobRunning"
              :latency-ms="jobLatency"
            />
          </div>
          <button type="button" class="btn btn-secondary" style="align-self:flex-start; margin-top:12px;"
                  @click="jobRunning = !jobRunning">
            {{ jobRunning ? 'Pausar demo' : 'Reanudar demo' }}
          </button>
        </div>
      </section>

      <section id="recorder" class="demo-section">
        <h2 class="demo-section__title">05 · Recorder Studio (live)</h2>
        <p class="demo-note" style="margin-bottom:16px;">
          Este bloque es el <strong>checkpoint</strong> del plan: graba takes, arrastra
          archivos, marca referencias y pulsa CREATE PROFILE. Las takes viven en memoria
          del navegador hasta el CREATE; <code>beforeunload</code> te avisa si sales con
          takes sin subir. El SNR del LED es un estimate cliente hasta que el backend
          devuelve el valor real (entonces se reemplaza).
        </p>
        <RecorderStudio @profile-created="(p) => console.log('profile created', p)" />
      </section>

      <footer class="demo-footer studio-value">
        <span>STUDIO SYSTEM · v0.2 · dark</span>
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
.demo-brand__mark { color: var(--accent); text-shadow: 0 0 12px var(--accent); }
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

.demo-hero { display: flex; flex-direction: column; gap: 20px; padding-top: 40px; }
.demo-hero__lede { max-width: 620px; color: var(--fg-1); font-size: 18px; line-height: 1.5; }

.demo-section { display: flex; flex-direction: column; gap: 16px; }
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
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.08em;
  text-transform: uppercase; color: #fff; mix-blend-mode: difference;
}
.sw code {
  font-family: var(--font-mono); font-size: 11px; color: #fff;
  mix-blend-mode: difference; opacity: 0.8;
}

.demo-type { padding: 28px 32px; display: flex; flex-direction: column; gap: 12px; }
.demo-card { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.demo-group { display: flex; gap: 32px; flex-wrap: wrap; align-items: center; }
.demo-note { font-family: var(--font-mono); font-size: 11px; color: var(--fg-2); letter-spacing: 0.04em; }

.demo-models { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.demo-side-by-side { display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap; }

.demo-footer {
  display: flex;
  justify-content: space-between;
  padding-top: 24px;
  border-top: 1px solid var(--line);
  color: var(--fg-2);
  font-variant-numeric: tabular-nums;
}
</style>
