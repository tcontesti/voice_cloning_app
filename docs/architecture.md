# Arquitectura — Voice Cloning App

> Hospital Universitario Son Llatzer. Despliegue on-prem. RGPD + Ley IA UE 2024/1689.

## Topología

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Frontend   │────▶│   FastAPI    │────▶│  PostgreSQL    │
│  (Vue 3)    │◀────│   Backend    │     └────────────────┘
└─────────────┘     └──────────────┘
       │                   │  │
       │ WebSocket         │  ▼
       │ (progreso)        │  ┌────────────┐
       │                   │  │   Redis    │ (cache embeddings + rate limit)
       │                   │  └────────────┘
       │                   │
       │                   ▼
       │            ┌──────────────┐        ┌──────────────┐
       └───────────▶│   RabbitMQ   │───────▶│ Worker       │
                    │   (jobs)     │        │ Chatterbox   │───▶ GPU (Spark)
                    └──────────────┘        ├──────────────┤
                           │                │ Worker       │
                           │                │ OmniVoice    │───▶ GPU (Spark)
                           │                ├──────────────┤
                           │                │ Worker       │
                           │                │ Qwen3-TTS    │───▶ GPU (Spark,
                           │                │              │     venv aislado)
                           │                └──────────────┘
                           ▼
                    ┌──────────────┐
                    │    MinIO     │ (SSE-C, KMS mock dev / Vault prod)
                    └──────────────┘
```

## Dev topology

- **Frontend + FastAPI**: Windows (hot-reload rápido).
- **Postgres, Redis, RabbitMQ, MinIO, Nginx**: Docker Compose local o en Spark.
- **Workers Celery (chatterbox / omnivoice / qwen3)**: Spark (acceso GPU).
- **Conexión dev**: SSH tunnel Windows → Spark para RabbitMQ/MinIO o VPN hospital.

## Lazy-load LRU de modelos

Cada worker arranca sin modelo cargado. Al recibir un job:
1. Si el modelo está cargado y fresco → úsalo.
2. Si no → unload del modelo LRU, load del solicitado.
3. Tras 10 min idle → unload automático (timer background).

Justificación: Spark comparte ~130 GB VRAM con MedGemma 27B y DermApixel. No podemos mantener 3 modelos TTS residentes.

## Venv aislados

- `~/voice_cloning_env/.venv` (Spark) — stack principal: torch cu130, chatterbox, omnivoice, torchaudio patched.
- `~/voice_cloning_qwen_env/.venv` (Spark) — stack Qwen3: `transformers<5`, qwen-tts.

El worker Qwen invoca Python del venv aislado vía `subprocess` con `sys.executable` parametrizado. No se importa nada de Qwen en el proceso Celery principal.

## Componentes clave (roadmap)

| Milestone | Entrega |
|-----------|---------|
| M1 | Scaffolding + healthchecks |
| M2 | Domain + auth mock OIDC + consent + audit hash chain |
| M3 | Recordings backend (SNR, VAD, MinIO) |
| M4 | Frontend base + `<VoiceRecorder>` |
| M5 | Pipeline síntesis Chatterbox end-to-end |
| M6 | Workers OmniVoice + Qwen3 |
| M7 | Paneles clínico / admin / auditor |
| M8 | Helm + Vault real + Keycloak + observabilidad |

## ADRs

Ver `docs/adr/` para decisiones no triviales.
