# voice_cloning_app

Material asociado al proyecto **"Preservación de la identidad vocal del paciente mediante clonación de voz zero-shot, watermarking y anti-spoofing en un entorno hospitalario on-premise"**. Aplicación clínica desarrollada por Marc Link Cladera, Andrés Borrás Santos y Antonio Contestí Coll (graduados en Ingeniería Informática por la Escola Politècnica Superior de la Universitat de les Illes Balears) en colaboración con la Dra. Amaya Roldán Fidalgo (FEA, Servicio de Otorrinolaringología y Cirugía de Cabeza y Cuello, Hospital Universitario Son Llàtzer — IB-Salut), bajo el marco del convenio UIB · IB-Salut · FUEIB.

Candidatura a los **Premios Salut Innova UIB-HLL Son Espases · 4ª edición (2026)**, categoría **IA y big data**.

El sistema permite que un paciente con patología que amenaza su voz (cáncer de laringe, cirugía de cabeza y cuello, ELA, intubación prolongada, daño neurológico) grabe segundos de voz residual o pre-quirúrgica desde una interfaz web, genere un perfil vocal cifrado en almacenamiento on-premise, y sintetice habla conservando su identidad acústica a partir de texto. Toda la inferencia ocurre dentro de la red hospitalaria, sin tránsito a la nube. Cada audio sintético lleva marca de agua imperceptible y queda registrado en un audit log append-only con cadena de hashes. La arquitectura combina tres familias de modelos open-weight evaluadas en un benchmark previo de 528 generaciones sobre castellano peninsular, una capa de anti-spoofing AASIST y una integración opcional con ElevenLabs (deshabilitada por defecto, no apta para datos clínicos) usada únicamente como techo aspiracional de calidad para comparativas no clínicas.

## Estructura del repositorio

```
voice_cloning_app/
├── backend/             FastAPI async + SQLAlchemy + Celery
│   ├── app/             API, dominio, adapters de modelos, postproc (AASIST, watermark)
│   ├── alembic/         migraciones
│   ├── tests/           pytest (auth, recordings, sintesis, audit chain)
│   └── Dockerfile
├── frontend/            Vue 3 + Vite + Tailwind 4 + Pinia + vue-i18n
│   ├── src/             VoiceRecorder, SpectrogramCanvas, VuMeter, consent flow
│   └── Dockerfile
├── worker/              workers nativos Spark (Celery) por modelo
│   ├── start_worker.sh  arranque foreground
│   └── systemd/         unit files (--user)
├── infra/               docker-compose, nginx, postgres init, keycloak, vault, observabilidad
│   ├── compose/         despliegue multi-host (PC + Spark)
│   ├── helm/vcapp/      chart Helm (M8)
│   └── keycloak/        realm de ejemplo (seeds dev)
├── scripts/             vault_bootstrap, dev_start, watchdog túnel
├── tests/load/          escenarios Locust
└── docs/                arquitectura, seguridad, RGPD, ADRs, landing
    ├── adr/             Architecture Decision Records
    ├── index.html       landing page (GitHub Pages)
    └── *.md             documentación técnica
```

El repositorio web del prototipo (este) contiene el código operativo. Los benchmarks previos sobre 4 modelos en castellano peninsular, su pipeline de evaluación reproducible (528 generaciones, métricas WER / UTMOS / WavLM / AASIST / watermark) y el informe ético-jurídico que motiva la exclusión de XTTS-v2 están documentados en el wiki.

## Cómo navegar este material

**Si quieres entender la propuesta a los premios:** abre `docs/Resumen_Ejecutivo_VoiceCloning.pdf` (2 páginas). Versión web equivalente en `docs/index.html` o en <https://tcontesti.github.io/voice_cloning_app/>.

**Si quieres entender la arquitectura del prototipo:** consulta `docs/architecture.md` y el wiki, página *Prototipo VoiceCloning*. El flujo extremo a extremo (frontend Vue → backend FastAPI → Celery worker en Spark GPU → postproceso watermark + AASIST → MinIO cifrado) está descrito allí.

**Si quieres desplegar el sistema en local:** sigue el *Quickstart* más abajo. Requiere Docker Compose y certificados TLS de desarrollo.

**Si quieres entender la selección de modelos:** consulta la página *Experimentos* del wiki y `docs/adr/0001-stack-choice.md`. Se documentan los decision gates (WER < 8%, UTMOS ≥ 3.5, WavLM > 0.75, TTFA < 3s, licencia permisiva, fallos < 5%) y los motivos de cada decisión.

**Si quieres revisar el marco ético y jurídico:** consulta `docs/rgpd_compliance.md` y `docs/security.md`. Se cubren consentimiento específico para clonación, watermarking obligatorio, anti-spoofing, audit log append-only y la posición sobre la licencia CPML de XTTS-v2.

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

## Modelos integrados

| Modelo | Licencia | Rol | Watermarking |
|---|---|---|---|
| Chatterbox | MIT | Por defecto | PerTh nativo (verificado 132/132) |
| OmniVoice | Apache 2.0 | Mejor similitud de locutor | AudioSeal post-hoc |
| Qwen3-TTS | Apache 2.0 | Alternativa (venv aislado, `transformers<5`) | AudioSeal post-hoc |
| ElevenLabs | API comercial | Solo comparativa no clínica (deshabilitado por defecto) | No detectable → no apta para clínica |
| XTTS-v2 | CPML | **Excluido** hasta dictamen jurídico | — |

Decisiones documentadas en `docs/adr/`.

## Reproducibilidad

Los workers se ejecutan **nativamente** sobre una NVIDIA DGX Spark (chip Grace Blackwell GB10, arquitectura ARM64, CUDA 13.0, 130 GB VRAM unificada). Los workers contenedorizados son una alternativa documentada pero no la ruta principal por VRAM/iteración. El benchmark previo de selección de modelos (528 generaciones, 4 locutores VoxPopuli-ES × 3 longitudes de referencia × 11 frases × 4 modelos, tasa de fallo 0%) está descrito en el wiki bajo *Experimentos*.

Los pesos pre-entrenados y los datasets externos (CommonVoice ES, VCTK, MLS, VoxPopuli-ES) están disponibles a través de sus repositorios oficiales según sus respectivas licencias. Este trabajo no redistribuye material de dichos datasets ni pesos de modelos: las imágenes Docker descargan los checkpoints en tiempo de arranque desde los registros originales.

## Cooperación UIB · IB-Salut

Proyecto desarrollado bajo el convenio UIB · IB-Salut · FUEIB. Equipo mixto:

- **UIB · Escola Politècnica Superior:** Marc Link Cladera, Andrés Borrás Santos, Antonio Contestí Coll (graduados en Ingeniería Informática).
- **IB-Salut · Hospital Universitario Son Llàtzer:** Dra. Amaya Roldán Fidalgo (FEA, Servicio de Otorrinolaringología y Cirugía de Cabeza y Cuello).

La selección de patología y escenarios clínicos, los protocolos de captura de voz residual y la validación perceptiva planificada (escucha ciega con logopedas y otorrinos) se realizan desde el Servicio de ORL del HUSLL. El diseño técnico, la implementación y la auditoría algorítmica se realizan desde la EPS-UIB.

## Licencia

Documento académico y código liberados bajo Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). Consultar `LICENSE` para detalles. El material de terceros (modelos base, datasets, implementaciones de referencia) conserva su licencia original — especialmente la licencia CPML de Coqui XTTS-v2, motivo de su exclusión hasta dictamen jurídico.

## Cita

```bibtex
@misc{voicecloning_husll_uib_2026,
  author       = {Link Cladera, Marc and Borr\'as Santos, Andr\'es and
                  Contest\'i Coll, Antonio},
  title        = {Preservaci\'on de la identidad vocal del paciente mediante
                  clonaci\'on de voz zero-shot, watermarking y anti-spoofing
                  en un entorno hospitalario on-premise},
  year         = {2026},
  howpublished = {Candidatura Premios Salut Innova UIB-HLL Son Espases,
                  4\textsuperscript{a} edici\'on. Universitat de les Illes
                  Balears, Escola Polit\`ecnica Superior; Hospital
                  Universitari Son Ll\`atzer, Servei
                  d'Otorrinolaringologia.},
  note         = {Colaboraci\'on cl\'inica: Dra. Amaya Rold\'an Fidalgo
                  (FEA ORL, HUSLL).}
}
```

## Contacto

- **Antonio Contestí Coll** — `toni.contesti.coll@gmail.com`
- **Marc Link Cladera** — UIB · EPS
- **Andrés Borrás Santos** — UIB · EPS
- **Colaboración clínica:** Dra. Amaya Roldán Fidalgo — Servicio de Otorrinolaringología y Cirugía de Cabeza y Cuello, Hospital Universitario Son Llàtzer (IB-Salut)
