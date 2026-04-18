# Revisión funcional — 2026-04-18

Branch: `main`. Alcance: frontend Vue 3 + backend FastAPI (sin tocar workers
Spark ni Docker). Baseline al arrancar: `vue-tsc`, `vitest` (10/10) y `vite
build` en verde. Todo lo fijado abajo mantiene los tres en verde.

> Pasada 2 (mismo día, tarde) — fixes reportados por usuario tras prueba
> E2E: B1–B6 y U1–U3. Ver sección al final.

## Resumen por flujo

| # | Flujo | Estado | Nota |
|---|---|---|---|
| F1 | Login | ✅ OK | Sin cambios. Happy-path + 401 + refresh cubiertos por tests. |
| F2 | Consent | ⚠️ parcial | Happy-path firma correctamente. Falta redirect-si-ya-firmado y guard downstream — requiere endpoint backend `GET /consent/me`. Documentado como pendiente, no se añade aquí (fuera del alcance "no nuevas features"). |
| F3 | Record | ✅ Fixed | Bug: upload de MP3/FLAC/OGG fallaba con 415 — backend solo acepta `audio/wav`. Fix: transcodificar el `AudioBuffer` decodificado a WAV antes de subir. |
| F4 | Profiles | ✅ OK | Listado, empty-state, USE → query `?profile=<id>`. USE no funcionaba porque SynthesizeView ignoraba la query (ver F5). |
| F5 | Synthesis | ✅ Fixed | Bugs: (a) `?profile=<id>` del botón USE se ignoraba; (b) download del audio sin filename. Ambos corregidos. Gaps pendientes (backend): modelo `elevenlabs` no se expone en `/synthesis/models`; flags `cloud`/`clinical_safe` no existen; modal de confirmación cloud depende de esos flags. |
| F6 | History | ✅ Fixed | Bugs críticos: play inline con `<audio :src>` y download con `<a :href>` NO envían `Authorization` → ambos daban 401. Fix: fetch con bearer + blob URL, download programático con filename. |
| F7 | Admin | ✅ OK | Users list, stats, PATCH active, self-deactivate bloqueado. Sin cambios. |
| F8 | Audit | ✅ OK | Logs paginados, filtros (action/prefix/since), chain integrity, payload expandible. Sin cambios. |
| F9 | Health | ✅ OK | Badge verde/ámbar/rojo, hover con detalle por servicio. Sin cambios en esta pasada (ya había diff previo en working-tree sin commitear). |
| F10 | Nav/Layout | ✅ OK* | Topbar role-based correcto. `*` Gap: en `<900px` la nav se oculta sin hamburger — UX degradada pero no bloqueante (usuario puede navegar por URL). |
| F11 | ElevenLabs | ⚠️ dead-code | OptionsPanel implementado y cablado por `selectedModel.includes('eleven')`. Como backend no devuelve modelo `elevenlabs`, nunca se activa. Marcado [SPARK-SIDE/BACKEND-SIDE]. |

## Bugs arreglados en esta pasada

1. **F3 — upload no-WAV rechazado**
   `frontend/src/ui/composites/RecorderStudio.vue`, `frontend/src/composables/useRecorder.ts`
   - `DeviceSelector` anuncia `WAV · MP3 · FLAC · OGG` pero el endpoint
     `POST /recordings` del backend solo acepta `audio/wav`.
   - Fix: `encodeWav` exportado; `buildTakeFromBlob` re-encoda el
     `AudioBuffer` decodificado a WAV (16-bit PCM mono) cuando el input
     no es WAV, manteniendo sampleRate nativo.

2. **F5 — USE de ProfilesView no preseleccionaba perfil**
   `frontend/src/views/SynthesizeView.vue`
   - `ProfilesView` navegaba a `/synthesize?profile=<id>` pero la view
     ignoraba `route.query.profile` y siempre elegía el primero de la
     lista.
   - Fix: leer `route.query.profile`, validar que sigue existiendo, y si
     no caer al primero.

3. **F5 — download del audio sin filename**
   `frontend/src/views/SynthesizeView.vue`
   - `<a :href="audioUrl" download>` sobre un blob URL descargaba el
     fichero con nombre aleatorio sin extensión.
   - Fix: `:download="\`synthesis-\${job?.id.slice(0,8)}.wav\`"`.

4. **F6 — play/download rotos en historial (crítico)**
   `frontend/src/views/HistoryView.vue`
   - `<audio :src>` y `<a :href>` sobre `/api/synthesis/:id/audio` no
     llevan el header `Authorization`; el endpoint es Bearer-protected,
     así que ambos devolvían 401 y el usuario no podía reproducir ni
     descargar nada del histórico.
   - Fix: fetch del audio con `Authorization: Bearer …`, blob URL cacheado
     por fila, y descarga vía `<a download=synthesis-XXXX.wav>` creado
     programáticamente. Cleanup en `onBeforeUnmount`.

## Gaps documentados (no arreglados aquí)

Estos no son bugs en código existente, son features pendientes o
extensiones que requieren trabajo de backend.

- **F2 — Redirect-si-ya-firmado + guard downstream**
  Requiere endpoint `GET /consent/me` → `{accepted, version, accepted_at}`,
  `consentApi.me()`, uso en `ConsentView.onMounted`, y un guard
  `requiresConsent` en el router (o store con estado consolidado).
  Alternativa más ligera: backend devuelve 403 desde
  `/recordings` / `/profiles` / `/synthesis` si el usuario no ha
  firmado, y el frontend redirige a `/consent` al ver ese 403.

- **F5 — Modal de confirmación cloud + footer "Procesado por ElevenLabs"**
  Requiere que `/synthesis/models` devuelva flags `cloud` y
  `clinical_safe` en `ModelInfo`, y que exista una opción ElevenLabs en
  esa lista. Sin eso, el flag nunca se evalúa.

- **F5 — Badge watermark scheme**
  UI muestra "WM VERIFICADO/AUSENTE" pero no el scheme
  (PerTh / AudioSeal). `SynthesisRow.watermark_scheme` ya viene del
  backend; falta surface-arlo en la badge. Polish, no funcional.

- **F10 — Nav mobile (`<900px`)**
  `.shell__nav { display: none }` sin hamburger replacement. La nav
  desaparece por completo en móvil. Fix implica añadir toggle +
  overlay — trabajo de UX, no bugfix.

- **F11 — ElevenLabs no expuesto**
  Backend `/synthesis/models` sólo devuelve chatterbox / omnivoice /
  qwen3tts. El frontend ya está listo (OptionsPanel + flag
  `selectedModel.includes('eleven')`) pero no hay datos que disparen
  la rama. [SPARK-SIDE/BACKEND-SIDE].

- **F8 — `datetime-local` vs timezone**
  Filtro "desde" envía `YYYY-MM-DDTHH:MM` (naive). FastAPI lo parsea
  como naive; postgres (si la columna es TIMESTAMPTZ) lo interpreta en
  UTC. Para la zona +2 de HSLL, las consultas tendrán 2h de offset
  silencioso. No es crítico, pero merece un `Z` o un helper explícito.
  No tocado aquí.

## Transversal

- ✅ `Authorization: Bearer <token>` auto-inyectado por `api/client.ts`
  en todos los requests excepto `/auth/login` y `/health`.
- ✅ 401 → `auth.logout()` + siguiente navegación cae al guard de
  `requiresAuth` → redirect a `/login`. Cubierto en `tests/unit/auth.spec.ts`.
- ✅ Vite proxy `/api/*` → backend con `ws: true` para `/ws/jobs/*`.
- ✅ vue-tsc --noEmit limpio tras los fixes.
- ✅ vitest `10/10`.
- ✅ vite build limpio (bundle ~67 KB gzip el chunk más grande).
- ⚠️ Errores 500 → se surfacea `(e as Error).message` en banners
  `role="alert"` o `role="status"`. No se ha inspeccionado en vivo con
  backend down; confiamos en que `fetch` rechaza con TypeError y cae al
  catch. Recomendable test e2e.
- ⚠️ CSP / HSTS en nginx prod: no tocado, fuera del alcance frontend.

## Baselines finales

- `npx vue-tsc --noEmit` → exit 0
- `npx vitest run` → 10/10
- `npx vite build` → exit 0, built in ~2.4s

---

## Pasada 2 — Fixes reportados por usuario (E2E)

Arreglos tras prueba end-to-end. Los items tachados en "Gaps" arriba que
ya quedan cubiertos se marcan aquí.

| # | Item | Estado | Commit |
|---|---|---|---|
| B1 | Login: eye/eyeoff password toggle | ✅ | `feat(ux): password show/hide toggle on login` |
| B2 | Record: play/pause por take + waveform con playhead + click seek | ✅ | `feat(record): play/pause + seekable waveform playhead on each take` |
| B3 | Synthesize: click-seek en waveform no funcionaba (audio doble) | ✅ | `fix(synthesis): unify playback on WaveformTimeline so seek actually works` |
| B4 | Synthesize: "audio 404" al cambiar de modelo y regenerar | ✅ | `fix(synthesis): clear audio + guard status on model-switch resubmits` |
| B5 | Synthesize: ElevenLabs no aparecía en /synthesis/models | ✅ | `fix(synthesis): sync elevenlabs enum + expose model` (combinado con B6) |
| B6 | **HIGH**: GET /synthesis → 500 (enum DB vs Python desalineado) | ✅ | ver B5 |
| U1 | ModelCards con métricas reales del benchmark 2026-04-14 | ✅ | `feat(ux): real benchmark metrics on ModelCards` |
| U2 | Profiles CRUD — renombrar, borrar, editar referencias | ✅ | `feat(ux): profiles CRUD` |
| U3 | Tarjeta "Detalles de generación" bajo el reproductor | ✅ | `feat(ux): generation metadata card under the synthesis player` |

### Cambios backend de esta pasada

- `SynthesisModel` enum Python extendida con `elevenlabs`.
- Migración Alembic **0004** — `ADD VALUE IF NOT EXISTS 'elevenlabs'`
  (idempotente; no-op en el DB multihost, necesaria para fresh installs).
- `celery_app.task_queues` declara `synth.elevenlabs`.
- Settings: `elevenlabs_enabled` + `elevenlabs_api_key` (ambos wired en
  `docker-compose.multihost.yml`).
- `/synthesis/models` expone el 4º modelo gated por
  `settings.elevenlabs_enabled`.
- Profiles API nuevos endpoints:
  - `PATCH /profiles/{id}` (nombre y/o refs, parciales)
  - `DELETE /profiles/{id}` → 204 OK, 409 si hay syntheses FK-restrict.
- Auditoría: acciones `profile.updated` y `profile.deleted`.

### Gaps actualizados

- ~~F5 Modal cloud~~ — ✅ cubierto por U3 (aviso amarillo "datos salen del
  hospital" cuando `model === 'elevenlabs'`). Modal bloqueante queda
  pendiente si se decide que el consentimiento por generación sea
  obligatorio.
- ~~F5 Badge watermark scheme~~ — ✅ ahora se muestra el scheme name
  (PerTh / AudioSeal) + ✓/✗ en el card de detalles.
- ~~F11 ElevenLabs no expuesto~~ — ✅ backend expone el modelo cuando el
  setting está activo; OptionsPanel se activa ahora automáticamente.
- F2 Consent-me endpoint — sigue pendiente.
- F10 Nav mobile hamburger — sigue pendiente.
- F8 timezone del filtro — sigue pendiente.

### Baselines pasada 2

- `npx vue-tsc --noEmit` → exit 0
- `npx vitest run` → 10/10
- `npx vite build` → exit 0
- Backend verificado en vivo: `GET /synthesis/models` devuelve 4 modelos,
  `GET /synthesis` devuelve 200 (antes 500), login + profiles endpoints
  OK.
