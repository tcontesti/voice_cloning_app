# ADR 0007 — Qwen3-TTS vía subprocess al venv aislado

**Fecha:** 2026-04-14
**Estado:** Aceptado

## Contexto

Qwen3-TTS requiere `transformers<5` y los shims de `_patches_qwen.py`. El venv principal corre `transformers>=5` para Chatterbox/OmniVoice. Co-instalar ambos no es posible — históricamente cada intento rompió uno de los dos.

Decisión histórica (overnight 2026-04-13): venv separado en
`~/voice_cloning_qwen_env/.venv` con su propio stack. Ya tiene Qwen3 y
`qwen-tts` instalados y validados (132 WAVs en el benchmark).

## Decisión

`Qwen3TTSAdapter` lanza un **subprocess long-lived** ejecutando
`worker/qwen_subprocess_worker.py` con
`~/voice_cloning_qwen_env/.venv/bin/python`. Comunicación por **JSON line-delimited** sobre stdin/stdout.

```
       parent (Celery worker, main venv)        child (qwen venv)
                  │                                    │
   load() ───────────► spawn(python -u qwen_subprocess_worker.py)
                  │                                    │  load model (~30s)
                  │  ◄──── {"ok":true,"ready":true}────│
                  │                                    │
   synthesize() ──► {"action":"synth","text":...}      │
                  │                                    │  generate_voice_clone()
                  │                                    │  write /tmp/vcqwen-<uuid>.wav
                  │  ◄── {"ok":true,"wav_path":...,...}│
                  │  read WAV; unlink                  │
                  │                                    │
   unload() ──────► {"action":"shutdown"}              │
                  │  ◄── {"ok":true,"bye":true}        │
                  │  wait(5s); SIGTERM; SIGKILL        │  exit 0
```

### Long-lived (no one-shot por petición)

Cargar Qwen3 cuesta ~30 s. Con one-shot pagamos eso por cada síntesis y
saturamos VRAM al alternar con MedGemma. Long-lived encaja perfectamente con
el LRU registry: `load()` spawn-ea, `unload()` (manual o por idle reaper a los
10 min) termina el subprocess y libera VRAM.

### Protocolo JSON line-delimited

- Una línea = un mensaje. Sin framing binario, sin protobuf — debug trivial
  con `cat`/`echo`.
- WAV no viaja por la pipe (binario en stdout es frágil, especialmente con
  `text=True`); se escribe en `/tmp/vcqwen-<uuid>.wav` y la respuesta
  devuelve la ruta.
- Comandos: `synth`, `ping`, `shutdown`. Extensible sin romper backwards.

### Errores y timeouts

- `READY_TIMEOUT_S=120`: tolera carga fría con margen.
- `CALL_TIMEOUT_S=600`: 10 min — más que suficiente para texto de 500 chars
  a RTF~4. Si se supera, SIGKILL al subprocess y `RuntimeError` en el task.
- Errores del child viajan como `{"ok": false, "error": "..."}` y se
  convierten en `RuntimeError` en el adapter, lo que el task de Celery atrapa
  y persiste como `Synthesis.status='failed'` + `error=...` en DB.
- EOF inesperado del child → drain del stderr y log con causa raíz.

### Concurrencia

`prefetch=1` en Celery + `threading.Lock()` en el adapter → un solo comando
en vuelo por proceso. No tenemos pipelining ni multiplexing intencionalmente
(complica el matching request↔response).

### Bypass de torch en el container backend

Mover `import _patches` desde top-level a `_lazy_import()` en
chatterbox.py y omnivoice.py. Esto permite que `app.workers.adapters` se
importe en el container backend (que no tiene `_patches` ni torch) sin
explotar. Los adapters siguen siendo no-ops hasta que `load()` los activa.

## Alternativas descartadas

- **Re-installar Qwen3 en el venv principal**: fracasó en M0 (overnight log
  dice "qwen3tts falla con SDPA shape mismatch" tras transformers 5.5).
- **One-shot subprocess por petición**: pagaríamos ~30 s de carga cada
  call → RTF efectivo arruinado.
- **gRPC entre venvs**: overkill para una pipe local. Añade dep, complica
  systemd, no aporta nada.
- **Ejecutar Celery worker enteramente en el qwen venv**: tendríamos que
  duplicar el código de orquestación, o instalar también celery+redis ahí.
  Cualquier toque en backend obligaría a re-sincronizar dos venvs.

## Verificación

- 51/51 backend tests pasan
- 5 nuevos tests para `Qwen3TTSAdapter` con un fake_qwen.py que habla el
  mismo protocolo (load/synth/unload/error path/dead process)
- `GET /synthesis/models` ahora devuelve los 3 modelos como `available=true`
- Smoke real con GPU = manual del usuario:
  ```bash
  # El qwen venv ya existe del overnight 2026-04-13
  ls -la ~/voice_cloning_qwen_env/.venv/bin/python
  # Tras install_into_venv.sh del main venv:
  bash worker/start_worker.sh qwen3tts
  # journalctl --user -u worker_qwen3 -f
  ```

## Pendientes

- M8: medir overhead real del subprocess en producción (esperado ~10 ms por
  síntesis de marshalling + WAV write+read).
- M8: rotar el subprocess al cabo de N tareas como guard contra fugas (idem
  `task_acks_late=True` en Celery — posible añadir a la `LRU registry`).
- Considerar mmap shared memory para WAVs grandes si el RTT del filesystem
  se vuelve cuello de botella (no lo es a esta escala).
