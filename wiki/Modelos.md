# Modelos

> [[Home]] · Modelos

Fichas de los modelos evaluados y de su estado en la aplicación clínica. Los resultados numéricos provienen del benchmark de 528 generaciones documentado en [[Experimentos]].

---

## Chatterbox · *modelo por defecto*

| Atributo | Valor |
|---|---|
| Licencia | MIT |
| Tipo | Zero-shot TTS open-weight |
| Origen | Resemble AI |
| Watermark nativo | PerTh (verificado 132/132 en el benchmark) |
| Anti-spoofing AASIST | 0.471 (detectable como sintético) |
| WER castellano | 8.0 % |
| UTMOS22 | 3.11 |
| Sim WavLM | 0.707 |
| TTFA | 3.2 s |
| RTF | 0.50 |
| VRAM | 3.6 GB |

**Por qué es el modelo por defecto:** licencia permisiva, watermark imperceptible embebido nativamente sin coste adicional, WER en el umbral aceptable, calidad MOS comparable al resto y operación real-time.

**Adaptador:** `backend/app/workers/adapters/chatterbox.py` (cola `synth.chatterbox`).

---

## OmniVoice · *mejor similitud de locutor*

| Atributo | Valor |
|---|---|
| Licencia | Apache 2.0 |
| Tipo | Zero-shot clone |
| Watermark nativo | No → AudioSeal post-hoc obligatorio |
| Anti-spoofing AASIST | 0.503 |
| WER castellano | 10.9 % |
| UTMOS22 | 2.67 |
| Sim WavLM | **0.787** (mejor del benchmark) |
| TTFA | 5.8 s |
| RTF | 1.27 |
| VRAM | 4.0 GB |

**Cuándo elegirlo:** cuando la prioridad clínica es preservar al máximo la identidad vocal del paciente y se acepta latencia mayor (mensajes pre-grabados, lectura de informes). En estos casos el AudioSeal post-hoc es obligatorio y se aplica en la fase de postproceso.

**Adaptador:** `backend/app/workers/adapters/omnivoice.py` (cola `synth.omnivoice`).

---

## Qwen3-TTS · *segundo candidato*

| Atributo | Valor |
|---|---|
| Licencia | Apache 2.0 |
| Tipo | LLM-based TTS |
| Watermark nativo | No → AudioSeal post-hoc obligatorio |
| Anti-spoofing AASIST | 0.629 (más detectable como sintético, deseable) |
| WER castellano | 8.6 % |
| UTMOS22 | **3.11** |
| Sim WavLM | 0.775 |
| TTFA | 6.3 s |
| RTF | 1.07 |
| VRAM | 3.6 GB |

**Notas operativas:** requiere venv aislado con `transformers<5` por incompatibilidad con la suite del sistema. Se ejecuta como subproceso (`worker/qwen_subprocess_worker.py`), comunicación JSON-line por stdin/stdout. Optimización con flash-attn pendiente.

**Cuándo elegirlo:** alternativa a Chatterbox cuando se necesita mejor similitud sin pasar al coste latencia de OmniVoice. Buen perfil combinado MOS + similitud + AASIST.

**Adaptador:** `backend/app/workers/adapters/qwen3.py` (cola `synth.qwen3`).

---

## XTTS-v2 · *excluido*

| Atributo | Valor |
|---|---|
| Licencia | CPML — Coqui Public Model License |
| Watermark nativo | No |
| Anti-spoofing AASIST | **0.053** (pasa por humano casi siempre) |
| WER castellano | 8.9 % |
| UTMOS22 | 2.60 |
| Sim WavLM | 0.670 |
| TTFA | **1.7 s** (mejor del benchmark) |
| RTF | **0.22** |
| VRAM | **1.96 GB** |

**Motivo de exclusión:** doble bloqueo — licencia CPML no avalada por Servicio Jurídico del hospital + AASIST ínfimo. Operativamente sería el más atractivo (real-time, bajo VRAM), pero su uso clínico sin dictamen jurídico favorable y sin pipeline AudioSeal obligatorio sería incompatible con el art. 50 de la Ley IA UE 2024/1689.

Reintroducible solo con (a) dictamen jurídico y (b) AudioSeal post-hoc activo verificado.

---

## ElevenLabs · *referencia comercial, no clínica*

| Atributo | Valor |
|---|---|
| Licencia | API comercial |
| Despliegue | Cloud (no on-prem) |
| Watermark | No detectable por el operador |
| Estado | Integrado pero **deshabilitado por defecto** |

**Posición:** *techo aspiracional* de calidad para comparativas no clínicas (voluntarios técnicos, datasets públicos). Bloqueado para datos de paciente por dos motivos:

1. Transferencia internacional a EE. UU. sin SCC firmado + DPA ausente.
2. Falta de watermark detectable → incumple art. 50 Ley IA UE.

Controles defensivos:
- `ELEVENLABS_ENABLED=false` por defecto.
- Modal de confirmación bloqueante en la UI.
- `external_processor="elevenlabs"`, `deployment_safe=false`, `watermark_scheme="none"` registrados en cada job.

**Adaptador:** `backend/app/workers/adapters/elevenlabs.py`.

---

## Postproceso obligatorio en todos los modelos activos

Cada job tras la inferencia pasa por:

1. **Watermarking.**
   - Chatterbox → `resemble-perth verify` (PerTh nativo) y almacenamiento de `watermark_verified=true`.
   - OmniVoice / Qwen3-TTS → `audioseal embed` post-hoc y `audioseal verify` para confirmar.
2. **Anti-spoofing AASIST.** Score numérico almacenado por job. Útil tanto para auditoría como para detectar artefactos del modelo.
3. **Validación de duración y nivel.** Normalización LUFS opcional, recorte de silencios al inicio/fin.

Ningún audio se entrega al cliente sin que `watermark_verified=true` (excepto el caso bloqueado ElevenLabs, que se persiste explícitamente como `scheme=none` y no se entrega a un flujo clínico).
