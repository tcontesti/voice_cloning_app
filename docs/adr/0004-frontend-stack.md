# ADR 0004 — Frontend stack y captura de audio

**Fecha:** 2026-04-14
**Estado:** Aceptado

## Decisión

- **Vue 3 + Composition API + `<script setup>`** + TypeScript strict.
- **Vite 6** + plugin oficial `@tailwindcss/vite` (Tailwind 4 sin postcss config).
- **Pinia** para estado, **Vue Router 4** con guard `requiresAuth`.
- **vue-i18n 10** legacy:false. Un solo locale activo (`es-ES`); estructura preparada para `ca-ES`.
- **WaveSurfer 7** (waveform en grabación).
- **Lucide** iconos.
- **Tokens de diseño**: paleta `accent-{50..900}` derivada de `#1E5AA8`, `success` `#0F766E`, `danger` `#B91C1C`, `Inter` (CDN rsms.me), `rounded-lg`.

## Captura de audio

WebRTC pipeline:

```
getUserMedia(channelCount: 1, EC+NR on)
   └─► AudioContext
         ├─► MediaStreamSource
         ├─► AnalyserNode (compartido) → SpectrogramCanvas + VuMeter
         └─► ScriptProcessorNode(4096) → Float32 chunks → WAV PCM 16k mono
```

**Por qué `ScriptProcessorNode` (deprecated) y no `AudioWorklet`:**

- AudioWorklet requiere registrar un módulo separado, message-passing, lifecycle más complejo. Para una captura simple a Float32 el ROI no compensa en MVP.
- `ScriptProcessorNode` está deprecated pero no eliminado; funciona en Chrome/Firefox/Safari/Edge actuales.
- M5+ migrará a AudioWorklet **si** se introduce mel-spectrogram real (que sí requiere DSP en worklet para no bloquear el main thread con FFTs grandes).

**Por qué WAV PCM 16-bit 16k mono:**

- Backend espera WAV (validador `audio/wav`).
- 16 kHz mono coincide con el rate al que webrtcvad opera y con lo que esperan los TTS clínicos zero-shot (chatterbox/omnivoice/qwen3 reusan referencias a 16/24 kHz; downsample server-side es trivial).
- 16-bit es estándar y suficiente para voz; el canal de captura de la mayoría de micros consumer no excede 16 bit ENOB de todos modos.

## Spectrogram approximation

`SpectrogramCanvas` usa `AnalyserNode.getByteFrequencyData()` (FFT 1024 lineal) con eje y log para simular log-mel visualmente. **No es mel real.** Para monitoreo durante grabación clínica es suficiente; para análisis científico habría que hacer el filterbank mel en AudioWorklet con WebAssembly o hacer la conversión server-side. Documentado como pendiente M5+.

## Topología dev (Windows ↔ Spark)

- Frontend en Windows: `npm run dev` en `localhost:5173`.
- Backend FastAPI en Windows o en Spark vía SSH tunnel / VPN. `VITE_API_BASE` en `.env.local` apunta donde haga falta.
- Vite dev server proxy `/api/*` → backend, mantiene cookies same-origin y evita CORS.

## Alternativas descartadas

- **Nuxt**: SSR no aporta valor en SPA clínica intra-hospital, complica deploy on-prem.
- **React + Vite**: la decisión de Vue ya estaba tomada en M0; mantener.
- **`MediaRecorder` directo**: solo emite Opus/WebM, requeriría transcoding server-side.
- **`recordrtc`**: añade peso por sólo wrapper sobre lo mismo.
- **Tailwind 3 + postcss**: TW4 elimina config JS, mejor DX para tokens hospital.

## Tests

- `vitest` + `happy-dom` para unit tests de stores y composables.
- `@vue/test-utils` listo para tests de componentes (M5+ cuando haya TextToSpeech).
- Playwright e2e queda para M8 (despliegue).

## Verificación M4

```bash
cd frontend
npm install
npm run typecheck   # 0 errors
npm run test        # 3/3 passing
npm run dev         # http://localhost:5173 → login mock OIDC funcional
```
