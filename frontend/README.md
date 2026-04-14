# vcapp-frontend

Vue 3 + Vite + Tailwind 4 + Pinia + Vue Router + vue-i18n.

## Quickstart (Windows / Mac / Linux)

```bash
cd frontend
cp .env.example .env.local      # ajusta VITE_API_BASE si el backend está en otra máquina
npm install
npm run dev                     # http://localhost:5173
```

Mientras desarrollas, el backend FastAPI puede correr:
- En la misma máquina (Docker Compose levantado vía `make up` desde la raíz).
- En la Spark vía SSH tunnel: `ssh -L 8000:localhost:8000 husll-spark-01`.
- En la Spark vía VPN hospital: ajusta `VITE_API_BASE`.

## Scripts

- `npm run dev` — servidor Vite con HMR
- `npm run build` — build prod (vue-tsc + vite build)
- `npm run typecheck` — sólo TypeScript
- `npm run test` — vitest unit tests
- `npm run lint` — ESLint

## Estructura

```
src/
├── api/         clientes HTTP tipados
├── components/  UI reutilizable (VoiceRecorder, SpectrogramCanvas, VuMeter)
├── composables/ hooks Vue (useRecorder, useDevices)
├── i18n/        es-ES (estructura lista para ca-ES)
├── layouts/     PublicLayout (login) + AppLayout (autenticado)
├── router/      Vue Router con guard requiresAuth
├── stores/      Pinia (auth)
└── views/       Login, Home, Consent, Record
```

## Tokens de diseño

Definidos en `src/style.css` con `@theme` (Tailwind 4):

- `accent-600` `#1E5AA8` — primario hospital
- `success-600` `#0F766E`
- `danger-600` `#B91C1C`
- Inter como sans-serif (CDN rsms.me)
- `rounded-lg` por defecto, sombras sutiles

## VoiceRecorder

`<VoiceRecorder>` es un componente self-contained que combina:

- Selector de dispositivo (`enumerateDevices`)
- Captura via `MediaStreamSource` + `ScriptProcessorNode` (compatibilidad universal; downsample a 16 kHz mono al detener)
- Waveform en vivo via WaveSurfer 7 + plugin Record
- Spectrograma propio (`<SpectrogramCanvas>`) sobre un `AnalyserNode` compartido (FFT 1024, viridis, eje log)
- VU meter (`<VuMeter>`) sobre el mismo analyser

Emite `recorded(RecorderResult)` con un Blob WAV PCM 16-bit 16 kHz mono listo para subir vía `recordingsApi.upload()`.

## Pendientes M5+

- AudioWorklet con mel-filterbank real (la versión actual es FFT lineal con eje log — visualmente equivalente, no mel)
- Wizard de 3 pasos con frases guiadas (`phrases.csv` del repo backend) y SNR check pre-grabación
- WebSocket de progreso de jobs (M5)
- ConsentModal modal-bloqueante reutilizable (ahora vive como ConsentView; al añadir flujos que requieran consent fresco se externaliza)
