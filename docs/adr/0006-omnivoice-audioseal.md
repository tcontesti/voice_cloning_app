# ADR 0006 — OmniVoice + AudioSeal post-hoc

**Fecha:** 2026-04-14
**Estado:** Aceptado

## Contexto

OmniVoice (k2-fsa, Apache-2.0) lidera la similitud de locutor en el benchmark 2026-04-13 (WavLM 0.787, ECAPA 0.756 vs. Chatterbox 0.707/0.661). Es candidato fuerte para preservación de identidad vocal en pacientes. Pero **no embebe watermark nativo** — necesitamos aplicarlo nosotros.

## Decisión

### Política watermark por modelo (`scheme_for_model`)

```
chatterbox  → ("perth",     False)   # ya viene embebido por Resemble
omnivoice   → ("audioseal", True)    # aplicar post-hoc + verificar
qwen3tts    → ("audioseal", True)    # idem (M7)
```

Centralizada en `app/workers/postproc/watermark.py`. Test
`test_watermark_policy.py` la pinea: añadir un modelo nuevo sin elegir
scheme falla en CI antes de poder mergear.

### AudioSeal a 16 kHz, normalización final a 24 kHz

`apply_audioseal()` resamplea a 16 kHz (rate nativo del generador), suma el
delta del watermark, y devuelve audio a 16 kHz. La verificación
(`verify_audioseal`) corre inmediatamente después al mismo rate, así el
watermark está intacto cuando lo medimos.

Después, `normalize.to_wav_bytes()` resamplea a 24 kHz para mantener la
política uniforme de salida (24 kHz mono PCM 16-bit -23 LUFS). Sí, esto
puede atenuar ligeramente el watermark frente a un detector posterior; el
trade-off es aceptable porque:

1. Nuestra verificación interna (`watermark_verified=true`) es lo que la
   ley exige para auditoría — y se hace antes del resample.
2. Audios a SR mixto en historial confunden al paciente y al UI.
3. AudioSeal está diseñado para ser robusto a resampling moderado; en
   pruebas internas (por hacer en M8) si la confidence cae sistemáticamente
   por debajo del umbral tras el 24 kHz, evaluamos emitir a 16 kHz para esos
   modelos.

### OmniVoiceAdapter

Reusa el patrón validado en M5 (ChatterboxAdapter): lazy import tras
`import _patches`, load/unload bajo el LRU registry, prompt cache por ruta
de referencia para amortizar speaker encoding cuando el paciente sintetiza
varios textos consecutivos con la misma referencia.

API confirmada del repo k2-fsa: `OmniVoice.from_pretrained("k2-fsa/OmniVoice")` →
`create_voice_clone_prompt(ref_audio, ref_text=None)` → `generate(text,
language="spanish", voice_clone_prompt=prompt)`. Sample rate nativo: 24 kHz.

### Cola dedicada `synth.omnivoice`

Ya estaba configurada en M5 (`celery_app.task_queues`). En M6 simplemente
añadimos el unit systemd `worker_omnivoice.service`. Los tests verifican que
`POST /synthesis {model: omnivoice}` rutea a `synth.omnivoice`.

### Compartir VRAM con Chatterbox vía LRU

Un único proceso worker por modelo. Cuando el LRU registry detecta que se
pide chatterbox y el adapter cargado es omnivoice (o viceversa) hace
`unload()` del anterior y `load()` del nuevo. Tras 10 min idle el modelo
también se descarga.

En la práctica con 5-20 pacientes/día y dos modelos, lo esperable es que
cada worker mantenga su modelo cargado el tiempo entre jobs (<10 min) y
no haya thrashing. Si llegamos a uso intensivo y el thrashing se vuelve
problema, M8 puede subir `UNLOAD_AFTER_S` o pin model por worker.

## Alternativas descartadas

- **Aplicar AudioSeal a 24 kHz**: el modelo está entrenado a 16 kHz, la
  watermarking es robusta pero la confidence baja. Mejor mantener el
  generator/detector en su rate nativo.
- **No emitir 24 kHz uniforme** (devolver el rate nativo del modelo): UI
  inconsistente, audios mezcla 16/24 kHz.
- **Aplicar otro esquema (Silent Cipher, SoundSlash)**: AudioSeal de Meta
  tiene MIT license, mejor mantenedor y benchmarks publicados. Cumple Ley IA
  art. 50 trivially.

## Verificación

- 46/46 tests pasan (5 nuevos: 4 de policy `scheme_for_model` + 1 de routing)
- `GET /synthesis/models` ahora lista omnivoice como `available=true`
- Worker code listo; smoke real con GPU = manual del usuario:
  ```bash
  bash worker/install_into_venv.sh    # añade audioseal>=0.1.4
  bash worker/start_worker.sh omnivoice
  ```

## Pendientes (M7 / M8)

- M7: Qwen3TTSAdapter con venv aislado `~/voice_cloning_qwen_env/.venv`
  invocado por subprocess (transformers<5).
- M8: medir attenuation real del watermark AudioSeal post-resample 24 kHz;
  decidir si se mantiene la política o se hace excepción.
