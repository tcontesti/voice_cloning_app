# Voice Cloning Clínico — Wiki

Material asociado al proyecto **"Preservación de la identidad vocal del paciente mediante clonación de voz zero-shot, watermarking y anti-spoofing en un entorno hospitalario on-premise"**, desarrollado en el marco del convenio UIB · IB-Salut · FUEIB y presentado a los **Premios Salut Innova UIB-HLL Son Espases · 4ª edición (2026)**, categoría *IA y big data*.

- **Coautores (equipo mixto):**
  - Dra. Amaya Roldán Fidalgo — FEA, Servicio de Otorrinolaringología y Cirugía de Cabeza y Cuello, Hospital Universitario Son Llàtzer (IB-Salut)
  - Andrés Borrás Santos — graduado en Ingeniería Informática, EPS-UIB
  - Marc Link Cladera — estudiante de Ingeniería Informática, EPS-UIB (TFG previsto para junio 2026)
  - Antonio Contestí Coll — estudiante de Ingeniería Informática, EPS-UIB (TFG previsto para junio 2026)
- **Marco:** Convenio UIB · IB-Salut · FUEIB

## Resumen ejecutivo

El trabajo aborda una necesidad concreta y poco cubierta en el entorno sanitario público: cómo permitir que un paciente con patología que amenaza su voz (cáncer de laringe, cirugía de cabeza y cuello, ELA, intubación prolongada, daño neurológico) conserve su identidad vocal mediante síntesis de habla, sin que ello exija enviar su voz fuera del hospital, sin licencia comercial restrictiva, y con garantías forenses suficientes para resistir el escrutinio del Reglamento General de Protección de Datos y de la Ley de IA UE 2024/1689.

La primera contribución es un **benchmark reproducible** sobre cuatro modelos open-weight de clonación de voz zero-shot en castellano peninsular: Chatterbox (MIT), OmniVoice (Apache 2.0), Qwen3-TTS (Apache 2.0) y XTTS-v2 (CPML). 528 generaciones (4 modelos × 4 locutores VoxPopuli-ES × 3 longitudes de referencia × 11 frases) con métricas automáticas WER (faster-whisper large-v3), UTMOS22 real, similitud WavLM-large y ECAPA-TDNN, AASIST anti-spoofing y verificación de marca de agua. Tasa de fallo del 0 %. Los *decision gates* (WER < 8 %, UTMOS ≥ 3.5, WavLM > 0.75, TTFA < 3 s, licencia permisiva, fallos < 5 %) se fijaron a priori, y la selección de modelos integrados en la aplicación clínica se justifica con esos datos.

La segunda contribución es un **pipeline de salvaguardas obligatorias** que acompaña a cada síntesis: marca de agua imperceptible (PerTh nativa en Chatterbox verificada 132/132, AudioSeal post-hoc en OmniVoice y Qwen3-TTS), score AASIST anti-spoofing almacenado por job, audit log *append-only* con cadena de hashes SHA-256, consentimiento específico para clonación distinto del consentimiento de grabación con base legal art. 9 RGPD para dato biométrico, y cifrado de almacenamiento (MinIO con KMS Vault transit).

La tercera contribución es la **aplicación clínica end-to-end**: frontend Vue 3 con grabador propio (spectrograma en vivo, VU meter, downsample a 16 kHz mono), backend FastAPI asíncrono con Celery y migraciones Alembic, workers nativos sobre la DGX Spark del hospital, OIDC vía Keycloak para piloto, observabilidad Prometheus + Grafana + Loki, y empaquetado completo en Docker Compose (PC + Spark) o Helm chart para Kubernetes en producción.

La cuarta contribución es una **postura clara sobre dependencias cloud**. La integración con ElevenLabs se mantiene como referencia de calidad comercial pero queda deshabilitada por defecto y bloqueada para datos clínicos: la transferencia internacional sin SCC firmado y la ausencia de marca de agua detectable la hacen incompatible con RGPD y con el art. 50 de la Ley IA UE 2024/1689. XTTS-v2 queda excluido por su licencia CPML hasta dictamen del Servicio Jurídico.

## Navegación del wiki

### Documento académico y licenciamiento

| Página | Contenido |
|---|---|
| [[Memoria-academica]] | Estructura prevista de la memoria académica del proyecto |
| [[Licencia-y-citacion]] | CC BY-NC 4.0, BibTeX, licencias de terceros (modelos open-weight, datasets, AudioSeal, AASIST) |

### Prototipo clínico

| Página | Contenido |
|---|---|
| [[Prototipo-VoiceCloning]] | Arquitectura Vue 3 + FastAPI + Celery + worker GPU, watermark, AASIST, audit chain |

### Trabajo experimental

| Página | Contenido |
|---|---|
| [[Experimentos]] | Mapa de experimentos: benchmark 528 generaciones, decision gates, hallazgos overnight |
| [[Modelos]] | Fichas de Chatterbox, OmniVoice, Qwen3-TTS, XTTS-v2 (excluido) y ElevenLabs (no clínico) |
| [[Dataset]] | VoxPopuli-ES, CommonVoice ES, VCTK, MLS, política de privacidad de muestras propias |

### Infraestructura y reproducibilidad

| Página | Contenido |
|---|---|
| [[Hardware]] | DGX Spark GB10, ARM64, CUDA 13, VRAM 130 GB, requisitos mínimos para piloto |
| [[Reproducibilidad]] | Cuatro escenarios prácticos: arrancar la app, evaluar un modelo, ejecutar benchmark, generar una muestra |

### Marco institucional y ético-jurídico

| Página | Contenido |
|---|---|
| [[Colaboraciones]] | UIB · EPS (3 graduados), IB-Salut · HUSLL · ORL (Dra. Amaya Roldán Fidalgo), convenio UIB · IB-Salut · FUEIB |
