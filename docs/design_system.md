# Studio Design System

Sistema de UI de la app de clonación de voz clínica. Estética de consola de
estudio / equipo DJ-MIDI, dark-first, clínica y accesible.

## Tokens

Tokens CSS en `frontend/src/ui/theme/tokens.css` + mapeo a utilidades Tailwind v4
en `frontend/src/ui/theme/index.css`. Tipografía: Inter Tight (UI) + JetBrains
Mono (labels técnicos) + Source Serif 4 (documentos legales).

Paleta principal (dark):

```
--bg-0 #0a0a0c   fondo canvas
--bg-1 #111114   superficie card
--bg-2 #17171c   superficie elevada
--bg-3 #1f1f26   hover/active
--accent #7c5cff violeta eléctrico
--signal-green/amber/red/blue  estados
```

## Utilidades globales

- `.studio-card` — superficie elevada con borde + sombra.
- `.studio-label` — ALL CAPS mono 11 px, opacidad 60%.
- `.studio-value` — mono medio tamaño para lecturas técnicas.
- `.display-1` / `.display-2` — titulares Inter Tight tight.
- `.btn` / `.btn-primary` / `.btn-secondary` / `.input` / `.label` / `.card`.

## Primitives (`frontend/src/ui/primitives/`)

- `Knob.vue` — rotatorio 270°, drag vertical, shift=fine, flechas teclado.
- `Fader.vue` — vertical con graduaciones.
- `PixelMeter.vue` — meter pixelado 48×5 horiz / 6×28 vert, RMS + peak hold.
- `SpectrumAnalyzer.vue` — FFT 1024, gradiente violeta→cian.
- `WaveformTimeline.vue` — wavesurfer 7 con estilo studio.
- `Switch.vue` — interruptor físico.
- `SegmentedDisplay.vue` — LCD segmentado (mono fósforo).
- `LED.vue` — indicador con glow y pulse opcional.

## Composites (`frontend/src/ui/composites/`)

- `InputChannel.vue` — strip de mixer.
- `TransportBar.vue` — barra inferior flotante.
- `RecorderStudio.vue` — surface completa de grabación multi-take + upload.
- `DeviceSelector.vue` — dropdown + upload de archivos.
- `TakeThumbnail.vue` — waveform mini desde AudioBuffer.
- `ModelCard.vue` — tarjeta selectable de modelo TTS.
- `JobMonitor.vue` — display estilo hardware del progreso.
- `OptionsPanel.vue` — panel slide-in para parámetros (ElevenLabs).

## Vistas migradas

| Vista               | Estado                        |
| ------------------- | ----------------------------- |
| `LoginView`         | Tratamiento detallado v1      |
| `ConsentView`       | Source Serif + drag-to-sign   |
| `RecordView`        | Envuelve `RecorderStudio`     |
| `SynthesizeView`    | Split ModelCard + JobMonitor  |
| `ProfilesView`      | **Nueva** — grid de cards     |
| `HistoryView`       | **Nueva** — tabla DAW         |
| `AdminUsersView`    | Tokens + tipografía (fase 2)  |
| `AuditLogView`      | Tokens + tipografía (fase 2)  |

## Playground

Ruta dev-only `/_ui` (montada sólo con `import.meta.env.DEV`), muestra todos
los primitives + composites en variantes para iterar visualmente. Bypass de
auth deliberado.

## Roadmap · fase 2

Tratamiento detallado pendiente, priorizado:

1. **AuditLogView con hash-chain coloreado**
   - Colores pastel por segmento de hash.
   - Badge "SIGNED ✓" superior con LED.
   - Filas terminal monospace completas (actual aplica tokens pero no aún
     el tratamiento *terminal* del spec).
2. **AdminUsersView avanzado**
   - Gráfica mini de actividad por usuario.
   - Bulk actions + paginación.
3. **Light theme**
   - Spec original marca dark-first; la paleta light no es mapping trivial
     (accent violeta se mantiene, fondos requieren ajuste de contraste AAA).
   - Propuesta inicial (v2, tentativa — no implementar sin revisar contraste):

     ```
     --bg-0 #f7f7fa
     --bg-1 #ffffff
     --bg-2 #eeeef2
     --bg-3 #dedee4
     --fg-0 #0a0a0c
     --fg-1 #3e3e48
     --fg-2 #6e6e78
     --accent #5a3fe0   /* más oscuro para AAA sobre blanco */
     ```

4. **Screenshots**
   - Spec pedía Playwright; se descartó por coste de browsers (~200 MB).
   - Instrucciones manuales: abrir `http://localhost:5173/_ui`, capturar
     con DevTools (Cmd/Ctrl+Shift+P → "Capture full size screenshot") y
     pegar en `docs/design_system/screenshots/`.
5. **ProfilesView — waveform real**
   - Actualmente el thumbnail del card es pseudo-random determinista por id.
   - Sustituir por waveform real pre-computado al crear el perfil (server
     podría devolver un array de buckets; cambio en backend).
6. **Accesibilidad — verificación formal**
   - Checkear contraste AAA con `axe-core` en CI.
   - Feedback háptico (`navigator.vibrate`) en móvil, toggle en prefs.

## Patrones

- `prefers-reduced-motion`: todos los shell/gradientes animados lo respetan.
- Focus visible: knobs/faders/sliders muestran box-shadow con color accent.
- ARIA: controles rotatorios usan `role="slider"` + `aria-valuenow/min/max`.
- El drag-to-sign del consentimiento es accesible por teclado (Enter/Space).

## Dependencias añadidas en commits anteriores

- `@fontsource-variable/inter-tight`
- `@fontsource/jetbrains-mono`
- `@fontsource/source-serif-4`
- `motion-v` (animaciones)
- `tailwindcss-animate`
- `wavesurfer.js` (v7)
