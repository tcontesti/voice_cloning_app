# Voice Cloning App — Hospital Son Llatzer

Aplicación clínica de clonación de voz zero-shot. **On-prem**. RGPD + Ley IA UE 2024/1689.

Pacientes con patología que amenaza su voz (cirugía laringe, ELA, cáncer cabeza y cuello, etc.) graban una referencia, la plataforma genera un perfil vocal, y posteriormente sintetiza habla conservando la identidad vocal del paciente.

> **Estado:** en desarrollo. Milestone actual: **M1 — Bootstrap infra**.

## Modelos aprobados por benchmark 2026-04-14

| Modelo | Licencia | Rol |
|---|---|---|
| Chatterbox | MIT | Default (watermark PerTh nativo) |
| OmniVoice | Apache 2.0 | Mejor similitud de locutor |
| Qwen3-TTS | Apache 2.0 | Alternativa (venv aislado, `transformers<5`) |

XTTS-v2 **excluido** hasta dictamen jurídico (CPML).

## Quickstart (M1)

Requiere Docker + Docker Compose v2. Genera certificados TLS de desarrollo antes de arrancar:

```bash
# Certificados self-signed dev (o usar mkcert)
openssl req -x509 -newkey rsa:2048 -nodes -keyout infra/nginx/certs/server.key \
    -out infra/nginx/certs/server.crt -days 365 \
    -subj "/CN=localhost"

make env    # crea .env desde .env.example — edita secrets
make up     # levanta postgres + redis + rabbitmq + minio + backend + nginx
make ps     # comprueba healthchecks
curl -fsS http://localhost:8000/health
```

UIs locales:

- Backend: <http://localhost:8000/health>, <http://localhost:8000/metrics>
- MinIO console: <http://localhost:9001>
- RabbitMQ management: <http://localhost:15672>
- Nginx TLS: <https://localhost/health>

## Estructura

```
voice_cloning_app/
├── backend/            FastAPI + workers Celery (M5+)
├── frontend/           Vue 3 + Vite (M4)
├── infra/              docker-compose, nginx, postgres init, helm (M8)
├── docs/
│   ├── architecture.md
│   └── adr/            Architecture Decision Records
├── .env.example
├── Makefile
└── pyproject.toml      workspace root (ruff + mypy + pytest)
```

## Roadmap

Ver `docs/architecture.md` §Roadmap.

## Desarrollo

- Tests backend: `make test`
- Lint: `make lint`
- Format: `make format`
- Logs: `make logs`
- Reset completo: `make clean` (elimina volúmenes — destructivo)

## Seguridad y cumplimiento

- TLS 1.3 obligatorio (nginx).
- Headers CSP / HSTS / X-Frame-Options por defecto.
- Logs en JSON, nunca contienen texto de síntesis ni embeddings.
- Audit log append-only con hash chain (M2).
- Watermarking obligatorio en toda síntesis (M5/M6).
- Consentimiento específico RGPD + Ley IA firmado antes de clonación (M2).

Ver `docs/adr/0001-stack-choice.md` para decisiones.
