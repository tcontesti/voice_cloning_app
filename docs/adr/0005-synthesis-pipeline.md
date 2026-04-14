# ADR 0005 — Pipeline de síntesis: Celery nativo en Spark + LRU + Redis pub/sub

**Fecha:** 2026-04-14
**Estado:** Aceptado (M5 entrega Chatterbox; M6 OmniVoice, M7 Qwen3)

## Contexto

Las síntesis son trabajos lentos (RTF 0.2–4.0, modelos de 600 MB–8 GB VRAM). No pueden bloquear el HTTP del API. La Spark comparte ~67 GB de VRAM con MedGemma 27B y DermApixel — no podemos mantener varios modelos TTS residentes.

## Decisión

### Worker nativo en la Spark (no Docker)

`systemd --user` lanza un worker Celery por modelo, ejecutándose con
`~/voice_cloning_env/.venv/bin/python`. Razón: ese venv ya tiene torch 2.11.0+cu130 + chatterbox + `_patches` validado en el benchmark; containerizar torch+CUDA en ARM64/GB10 dobla el coste de iteración y rompe el acceso a `~/voice_cloning/models/`.

Backend NO se instala en el venv. Se añade a PYTHONPATH desde
`worker/start_worker.sh`. Solo añadimos a ese venv las deps "ligeras" listadas
en `worker/requirements-extra.txt` (celery, redis, sqlalchemy, minio,
resemble-perth). `install_into_venv.sh` verifica que torch sigue siendo cu130
después y aborta si se ha downgradeado.

### Una cola por modelo

Exchange `synth` direct con routing keys `synth.chatterbox`, `synth.omnivoice`,
`synth.qwen3tts`. Esto permite escalar horizontalmente cada modelo por separado
y aislar fallos. Rutado dinámico por kwargs en `task_routes`.

`worker_prefetch_multiplier=1` + `task_acks_late=True`: un job a la vez por
worker, ack solo tras éxito. Si el worker muere, RabbitMQ re-encola.
`worker_max_tasks_per_child=50` recicla periódicamente contra fugas de memoria.

### Lazy-load LRU con unload tras 10 min idle

`app/workers/registry.py` mantiene como mucho un adapter cargado por proceso.
Cambio de modelo → unload del anterior. Hilo background `vcapp-lru-reaper` cada
30 s comprueba si el modelo lleva idle más de 600 s y lo descarga.

Como Celery está en prefetch=1, no hay carrera entre tareas dentro del mismo
worker; el lock interno del registry sólo protege contra reaper vs. get().

### Watermark: PerTh sólo verificación (Chatterbox embebe nativo)

Chatterbox emite watermark PerTh durante `model.generate()`. El worker NO
aplica watermark — sólo verifica con `resemble-perth` que sobrevivió al
post-procesado. Si la verificación falla, log nivel ERROR y la fila guarda
`watermark_verified=false`. Hard policy en M6+ podrá fallar el job entero.

OmniVoice (M6) y Qwen3 (M7) no tienen watermark nativo → aplicaremos AudioSeal
post-hoc en el mismo punto del pipeline.

### AASIST anti-spoofing

Cada síntesis pasa por AASIST y se guarda `aasist_score` (probabilidad de
spoof, 0..1). No bloquea el job. Sirve como métrica para el informe clínico
y para detectar drift en la calidad del modelo.

### Normalización fija: 24 kHz mono PCM 16-bit, -23 LUFS

Todo audio sintetizado se entrega en este formato. Razón:
- 24 kHz: nativo de Chatterbox; OmniVoice/Qwen3 también producen 24 kHz.
- Mono: caso clínico no requiere espacial.
- -23 LUFS: estándar EBU R128 broadcast, evita audios "demasiado bajos" o
  "demasiado altos" entre síntesis distintas que confunden al paciente.

### Progreso vía Redis pub/sub (no aio-pika)

Worker publica eventos a `progress:job:<synthesis_id>` (canal Redis).
FastAPI WebSocket `/ws/jobs/{id}` se suscribe con `redis.asyncio` y reenvía.

Por qué Redis y no aio-pika sobre el mismo RabbitMQ:
- Redis ya está en el stack (cache, rate-limit). Una dep menos.
- Pub/sub es fire-and-forget — encaja perfectamente con eventos de progreso
  (si nadie escucha, no importa, el job sigue).
- aio-pika añade complejidad de exchanges fanout para algo no-crítico.

Snapshot inicial: cuando el WS se conecta lee la fila actual de DB y la envía
como primer frame, así un cliente que se conecta tarde no se queda en blanco.

### Auth WebSocket vía query param

Browsers no permiten `Authorization` en WebSocket → JWT viaja como
`?token=<jwt>`. Validación idéntica a HTTP. Sólo se acepta si el `synthesis_id`
pertenece al usuario del token. nginx ya tiene `proxy_pass` con upgrade.

## Alternativas descartadas

- **Docker para el worker**: torch+CUDA ARM64 doblaría tiempo de build, requiere
  bind-mount de modelos. El venv existente está validado.
- **Modelos siempre cargados (no LRU)**: no caben los 3 simultáneamente con
  MedGemma+DermApixel residentes.
- **WebSocket directo desde Celery**: imposible, Celery no es proceso async.
- **SSE (Server-Sent Events)** en lugar de WS: válido, pero WS permite enviar
  comandos cliente→servidor en M6+ (cancel job).
- **Polling /synthesis/{id}**: barato pero feo en UI; lo dejamos como fallback
  para entornos sin WS.

## Verificación

- 41/41 backend tests pasan (incluye 7 nuevos para /profiles, /synthesis, audit chain integridad post-flujo)
- Frontend `vue-tsc --noEmit` 0 errores; vitest 3/3
- Migración 0003 aplicada en dev DB; `GET /synthesis/models` responde
- Worker se arranca con `bash worker/start_worker.sh chatterbox` (validación e2e con job real queda como smoke manual del usuario en próxima sesión)

## Pendientes

- M6: adapter OmniVoice + AudioSeal apply+verify
- M7: adapter Qwen3 con venv `~/voice_cloning_qwen_env/.venv` (subprocess invocation)
- M6+: cancel job vía WS bidireccional
- Métricas Prometheus por modelo (RTF, VRAM peak, jobs/h) — ya tenemos prometheus-client; expose en M8
