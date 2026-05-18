# Licencia y citación

> [[Home]] · Licencia y citación

## Licencia del repositorio

Todo el material original de este repositorio (memoria, documentación, configuración y código propio) se publica bajo **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**. Texto completo en `LICENSE`.

**Permitido:**
- Compartir — copiar y redistribuir en cualquier medio o formato.
- Adaptar — remezclar, transformar y construir a partir del material.

**Bajo las siguientes condiciones:**
- **Atribución** — debe darse crédito apropiado, proporcionar un enlace a la licencia e indicar si se hicieron cambios.
- **No comercial** — no puede utilizarse para fines comerciales.
- **Sin restricciones adicionales** — no pueden aplicarse términos legales o medidas tecnológicas que restrinjan legalmente a otros hacer cualquier uso permitido por la licencia.

El material clínico, las muestras de voz de pacientes y los embeddings derivados quedan **fuera del repositorio** por su condición de dato biométrico sensible (RGPD art. 9). No se publican, no se redistribuyen, no salen del entorno hospitalario.

## Licencias de terceros integrados

| Componente | Licencia | Uso en el proyecto |
|---|---|---|
| Chatterbox | MIT | Modelo TTS por defecto; integrado vía pip, sin redistribución de pesos |
| OmniVoice | Apache 2.0 | Modelo alternativo; pesos descargados en arranque |
| Qwen3-TTS | Apache 2.0 | Modelo alternativo; venv aislado `transformers<5` |
| XTTS-v2 (Coqui) | CPML — *Coqui Public Model License* | **Excluido del despliegue clínico** hasta dictamen jurídico |
| AASIST | Restricted academic license (clovaai) | Anti-spoofing; código y pesos en `$VC_AASIST_DIR`, no redistribuidos |
| AudioSeal | MIT (Meta) | Watermarking post-hoc para OmniVoice / Qwen3-TTS |
| resemble-perth | MIT | Detector de watermark PerTh |
| faster-whisper | MIT | ASR para cálculo de WER en benchmark |
| WavLM | MIT (microsoft/wavlm-large) | Embeddings para métrica de similitud de locutor |
| ECAPA-TDNN | SpeechBrain (Apache 2.0) | Embeddings baseline de speaker verification |
| UTMOS22 | tarepan/SpeechMOS (Apache 2.0) | MOS predictor de referencia |
| VoxPopuli, CommonVoice, VCTK, MLS | Licencias originales | Datasets de referencia para benchmark; no redistribuidos |

## Posición sobre XTTS-v2

XTTS-v2 supera a varios modelos en latencia (TTFA 1.7 s, RTF 0.22) y obtiene WER aceptable (8.9 %) en castellano. Queda **excluido del despliegue clínico** por dos motivos:

1. **Licencia CPML** — la *Coqui Public Model License* impone restricciones que el Servicio Jurídico del hospital no ha avalado para uso asistencial.
2. **AASIST score 0.053** — el modelo pasa por humano en casi todos los casos del benchmark. En ausencia de marca de agua imperceptible nativa, su uso clínico sin AudioSeal post-hoc obligatorio sería incompatible con el art. 50 de la Ley IA UE 2024/1689 sobre trazabilidad de contenido sintético.

Reintroducible solo con: (a) dictamen jurídico favorable sobre CPML, y (b) pipeline AudioSeal post-hoc activo y verificado.

## Posición sobre ElevenLabs

ElevenLabs queda integrada como adaptador opcional **únicamente como referencia de calidad comercial para comparativas no clínicas** (voluntarios técnicos, datasets públicos). No es desplegable bajo RGPD ni Ley IA UE 2024/1689 por:

1. Procesamiento fuera de la red hospitalaria (transferencia internacional a EE. UU. sin SCC firmado, DPA ausente).
2. El modelo no expone marca de agua detectable al operador — incumple art. 50 sobre trazabilidad.

Controles defensivos en el código:
- Flag `ELEVENLABS_ENABLED=false` por defecto en `.env`.
- Modal de confirmación bloqueante en la UI antes de cualquier envío.
- Cada job auditado con `external_processor="elevenlabs"`, `deployment_safe=false`, `watermark_scheme="none"`.

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
                  Universitari Son Ll\`atzer, Servei d'Otorrinolaringologia.},
  note         = {Colaboraci\'on cl\'inica: Dra. Amaya Rold\'an Fidalgo
                  (FEA ORL, HUSLL).}
}
```
