# ADR 0001 — Stack técnico

**Fecha:** 2026-04-14
**Estado:** Aceptado
**Contexto del proyecto:** Aplicación clínica de clonación de voz, despliegue on-prem en DGX Spark (ARM64, CUDA 13), RGPD + Ley IA UE 2024/1689.

## Decisión

| Capa | Elección | Alternativas descartadas |
|---|---|---|
| Backend API | **FastAPI + Pydantic v2 + SQLAlchemy 2** | Flask (menos async), Django (demasiado framework), Litestar (menor ecosistema) |
| DB | **PostgreSQL 16** | MySQL (peor JSONB / extensiones crypto) |
| Cola | **RabbitMQ 3.13 + Celery** | Redis Streams (menos robusto), Kafka (overkill), Dramatiq (menos maduro en hospitales) |
| Cache | **Redis 7** | Memcached (sin persistencia), Dragonfly (menos probado on-prem) |
| Object store | **MinIO** | S3 real (off-prem), SeaweedFS (menos maduro) |
| Front | **Vue 3 + Vite + Tailwind 4** | React (preferencia del equipo por Vue), Svelte (ecosistema menor) |
| Auth | **Mock OIDC dev → Keycloak prod** | Auth0 (SaaS, no cumple on-prem), Authentik (menos adopción) |
| Audit | **Tabla append-only con hash chain SHA-256** | Append-only log externo (más infra), event store (overkill) |
| Watermark | **PerTh (chatterbox nativo) + AudioSeal post-hoc (resto)** | Solo AudioSeal (no detecta PerTh), marcas inaudibles comerciales (licencia) |
| Anti-spoof | **AASIST** | RawBoost, AASIST-SSL (más pesado, gain marginal) |
| Observabilidad | **Prometheus + Grafana + Loki** | ELK (más pesado), Datadog (SaaS) |

## Razones

1. **On-prem obligatorio** → descartado todo SaaS. Keycloak cubre OIDC sin dependencia externa.
2. **ARM64 + CUDA 13 + VRAM compartida** → workers Celery independientes con lazy-load LRU + venv aislado para Qwen3.
3. **RGPD + Ley IA** → hash chain en audit (verificable, barato), watermarking obligatorio en WAVs generados.
4. **Escala prevista 5–20 pacientes/día → 50–100/día** → RabbitMQ+Celery sobra; no justifica KEDA ni mesh.

## Consecuencias

- Un único stack Python en backend (FastAPI + Celery) simplifica mantenimiento.
- Vue 3 + Composition API + Pinia reutilizable como plantilla para otros proyectos del hospital.
- Hash chain requiere tests anti-tampering (parte de M2).
- Qwen3 con venv aislado implica `subprocess` overhead (~200 ms extra por job) — aceptable dado que RTF ~1.

## Revisión

- Reabrir si XTTS-v2 recibe dictamen jurídico favorable (añadir sin romper contrato).
- Reabrir si Vault no se despliega en hospital en 6m (evaluar SOPS + age como fallback).
