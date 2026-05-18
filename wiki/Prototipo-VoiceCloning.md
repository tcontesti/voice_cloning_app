# Prototipo VoiceCloning

> [[Home]] · Prototipo VoiceCloning

Aplicación web operativa de clonación de voz clínica. Despliegue íntegro on-premise sobre infraestructura hospitalaria. Cada audio sintético pasa por marca de agua, anti-spoofing y audit log antes de ser entregado.

## Diagrama de alto nivel

```
Paciente / Clínico
   │
   ▼  HTTPS  (Vue 3 + Vite + Tailwind 4)
[ Frontend ]
   │  REST async  + WS de progreso
   ▼
[ Backend FastAPI ]  ◄────►  [ PostgreSQL ]   (6 tablas, audit chain)
   │
   │  AMQP  ·  synth.<model>
   ▼
[ RabbitMQ 3.13 ]  ◄────►  [ Redis pub/sub ]   (progreso por job)
   │
   ▼
[ Worker nativo · DGX Spark ]
   │  modelo (Chatterbox | OmniVoice | Qwen3-TTS)
   ▼
[ Postproceso ]
   ├─ Watermark · PerTh nativo o AudioSeal post-hoc
   └─ AASIST anti-spoofing scoring
   │
   ▼
[ MinIO + KMS Vault ]   (almacenamiento cifrado SSE-C o transit)
```

## Stack tecnológico

| Capa | Tecnología | Notas |
|---|---|---|
| Frontend | Vue 3.5 + Vite + Tailwind 4 + Pinia + vue-i18n | i18n preparado para `es-ES`/`ca-ES` |
| Captura de voz | `MediaStreamSource` + `ScriptProcessorNode` | Downsample a 16 kHz mono, WAV PCM 16-bit |
| Visualización | WaveSurfer 7 + Record + Spectrogram propio | FFT 1024, viridis, eje log |
| Backend | FastAPI 0.115 async + SQLAlchemy 2 (async) + Alembic | Mock-OIDC HS256 → Keycloak (M9) |
| Cola | RabbitMQ 3.13 | Una cola por modelo (`synth.chatterbox`, `synth.omnivoice`, `synth.qwen3`) |
| Backend de progreso | Redis pub/sub | WS `/api/ws/jobs/{id}` |
| DB relacional | PostgreSQL 16 | Migraciones Alembic |
| Storage | MinIO (S3-compatible) | SSE-C en prod, KMS Vault transit |
| Workers | Celery 5 nativos sobre DGX Spark | LRU eviction tras 10 min idle |
| Postproc watermark | `resemble-perth` (verify) · AudioSeal (embed + verify) | PerTh nativo Chatterbox · AudioSeal post-hoc OmniVoice / Qwen3 |
| Postproc anti-spoofing | AASIST (`clovaai/aasist`) | Score persistido por job |
| Auth | OIDC (Keycloak en piloto, mock HS256 en dev) | Roles: `paciente`, `clinico`, `admin`, `auditor` |
| Reverse proxy / TLS | Nginx 1.25 | TLS 1.3, HSTS, CSP estricta |
| Observabilidad | Prometheus + Grafana + Loki | `docker-compose.observability.yml` |
| Empaquetado prod | Helm chart `infra/helm/vcapp` | ExternalSecrets / SealedSecrets |

## Modelos integrados

Decisiones documentadas en `docs/adr/` y en [[Modelos]]:

| Modelo | Licencia | Rol | Watermark | Estado |
|---|---|---|---|---|
| Chatterbox | MIT | Por defecto | PerTh nativo · verificado 132/132 | Activo |
| OmniVoice | Apache 2.0 | Mejor similitud de locutor | AudioSeal post-hoc | Activo |
| Qwen3-TTS | Apache 2.0 | Alternativa avanzada | AudioSeal post-hoc | Activo (venv aislado) |
| ElevenLabs | API comercial | Solo comparativa no clínica | No detectable | Bloqueado por defecto |
| XTTS-v2 | CPML | — | — | Excluido (ver [[Licencia-y-citacion]]) |

## Flujo end-to-end (caso de uso clínico)

1. **Consentimiento.** El paciente firma un consentimiento específico para clonación, distinto del consentimiento de grabación. El servidor renderiza el texto a HTML, lo persiste con `consent_version` y queda registrado en audit log.
2. **Grabación de referencia.** Frontend con grabador propio: el paciente lee frases controladas, ve spectrograma + VU meter en vivo. Al detener, se reentrega WAV PCM 16-bit 16 kHz mono.
3. **Subida y validación.** Backend valida formato, duración mínima y SNR. Persiste un `recording` con sha256, guarda el WAV cifrado en MinIO.
4. **Creación del perfil de voz.** Backend asocia uno o varios `recordings` a un `voice_profile`.
5. **Síntesis.** El clínico (o el propio paciente si tiene rol) crea una síntesis: `(profile_id, model, text)`. Backend persiste fila `synthesis (status=queued)` y publica a la cola del modelo.
6. **Worker.** Worker nativo recoge el job, carga el modelo (LRU 10 min), genera el audio, aplica watermark (nativo o post-hoc) y AASIST, persiste métricas (`watermark_verified`, `aasist_score`, `latency_ms`).
7. **Entrega.** Frontend recibe el WAV firmado, lo reproduce/descarga. Audit log graba la entrega.

## Seguridad y cumplimiento

- TLS 1.3 obligatorio.
- HSTS, CSP estricta, X-Frame-Options.
- Logs JSON; nunca contienen texto de síntesis ni embeddings de voz.
- Audit log append-only con cadena de hashes SHA-256 verificable (`/audit/verify`).
- Watermark obligatorio en toda síntesis; sin watermark, no se entrega.
- Anti-spoofing AASIST en cada job; score consultable por el auditor.
- Consentimiento específico con base legal art. 9 RGPD.
- Cumplimiento art. 50 Ley IA UE 2024/1689 (trazabilidad de contenido sintético).

## Latencias observadas (DGX Spark GB10)

| Modelo | TTFA | RTF | VRAM | Calidad |
|---|---|---|---|---|
| XTTS-v2 (excluido) | 1.7 s | 0.22 | 1.96 GB | WER 8.9 %, UTMOS 2.60 |
| Chatterbox | 3.2 s | 0.50 | 3.6 GB | WER 8.0 %, UTMOS 3.11, sim WavLM 0.71 |
| OmniVoice | 5.8 s | 1.27 | 4.0 GB | WER 10.9 %, UTMOS 2.67, sim WavLM 0.79 |
| Qwen3-TTS | 6.3 s | 1.07 | 3.6 GB | WER 8.6 %, UTMOS 3.11, sim WavLM 0.77 |

Latencias E2E (incluye HTTP, cola, modelo, postproc) en el orden de **3–7 s** según modelo.

## Despliegue de referencia

- **Dev local (todo en PC):** `make up` levanta postgres, redis, rabbitmq, minio, backend, nginx vía Docker Compose. Frontend con `npm run dev`.
- **Piloto multi-host (PC + Spark):** Docker Compose en la Spark expone postgres/redis/rabbitmq/minio; backend corre en PC y alcanza la Spark vía túnel SSH (autossh con watchdog). Documentado en `docs/dev_multihost.md`.
- **Producción:** Helm chart `infra/helm/vcapp` sobre Kubernetes hospitalario. ExternalSecrets para credenciales. Vault transit para KMS.

## Archivos de referencia

- `docs/architecture.md`
- `docs/security.md`
- `docs/rgpd_compliance.md`
- `docs/deployment.md`
- `docs/adr/`
