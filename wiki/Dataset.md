# Dataset

> [[Home]] · Dataset

Esta página describe los datasets utilizados en el benchmark y la política de privacidad aplicada a las muestras de voz, que son **dato biométrico sensible** bajo el art. 9 del RGPD.

## Datasets de referencia (benchmark)

| Dataset | Uso | Licencia | Redistribuido en este repo |
|---|---|---|---|
| **VoxPopuli-ES** | Locutores de referencia para el benchmark (4 hablantes: 2M + 2F) | CC0 (audio EP) + CC BY 4.0 (transcripciones) | No |
| **CommonVoice ES (Mozilla)** | Conjunto de evaluación humana planificado | CC0 | No |
| **VCTK** | Baseline para evaluación de similitud de locutor | Open Data Commons | No |
| **MLS (Multilingual LibriSpeech)** | Benchmark multilingüe con castellano | CC BY 4.0 | No |
| **EHR-Speech** (si disponible) | Evaluación en dominio clínico (futuro) | Bajo solicitud | No |

Este repositorio **no redistribuye** material de estos datasets. Las imágenes Docker y los scripts de descarga apuntan a los repositorios oficiales y respetan las licencias de origen.

## Datos propios (en el hospital, no públicos)

Las muestras grabadas en el hospital — voz residual o pre-quirúrgica de pacientes con patología vocal — son dato biométrico sensible y **no abandonan el entorno hospitalario**.

### Política de privacidad aplicada

| Aspecto | Implementación |
|---|---|
| Base legal | Consentimiento específico para clonación, art. 9.2.a RGPD |
| Almacenamiento | MinIO cifrado en reposo (SSE-C o transit Vault) dentro de la red hospitalaria |
| Tránsito | TLS 1.3 obligatorio entre frontend, backend y workers |
| Retención | Definida en el consentimiento; revocable por el paciente |
| Transferencia internacional | **Ninguna**. ElevenLabs, único módulo cloud, bloqueado para datos clínicos |
| Acceso | Limitado por rol (paciente, clínico, admin, auditor) vía OIDC |
| Auditoría | Cada acceso queda en audit log append-only con hash chain |
| Derechos del interesado | Acceso, rectificación, supresión, oposición, portabilidad, no decisiones automatizadas |
| Marca de agua | Toda síntesis derivada lleva PerTh / AudioSeal detectable |
| Anti-spoofing | Score AASIST almacenado por job |

### Detalles operativos

- **Captura.** Frontend con grabador propio. Downsample a 16 kHz mono PCM 16-bit. SHA-256 del WAV se calcula en el backend antes de cifrar.
- **Almacenamiento.** Bucket `recordings` para fuentes, bucket `syntheses` para salidas. Ambos con cifrado.
- **Logs.** En formato JSON. Nunca contienen el texto de la síntesis ni embeddings de voz.
- **Eliminación.** Soft-delete con marca y purga programada tras el periodo de retención.

## Cobertura lingüística

| Idioma | Estado |
|---|---|
| Castellano peninsular | Soporte principal · benchmark realizado |
| Catalán | Soporte preparado en frontend (i18n) · evaluación de modelos pendiente |
| Inglés | Soporte teórico de los modelos · sin evaluación local |

## Conjuntos de prueba (benchmark)

- **4 locutores VoxPopuli-ES** (2M + 2F).
- **3 longitudes de referencia:** 3 s, 10 s, 30 s.
- **11 frases** combinando vocabulario hospitalario, conversacional y números/nombres propios para medir pronunciación real.
- **Total:** 4 × 4 × 3 × 11 = 528 generaciones, tasa de fallo 0 %.

Ver [[Experimentos]] para resultados completos.
