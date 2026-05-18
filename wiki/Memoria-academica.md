# Memoria académica

> [[Home]] · Memoria académica

La memoria académica del proyecto está pendiente de redacción. Esta página recoge la estructura prevista y los materiales fuente disponibles para alimentarla. Mientras la memoria no esté disponible como PDF, el material formal evaluable para los Premios Salut Innova es el [Resumen Ejecutivo](https://github.com/tcontesti/voice_cloning_app/blob/main/docs/Resumen_Ejecutivo_VoiceCloning.pdf) (2 páginas), complementado con el repositorio, esta wiki y la [landing](https://tcontesti.github.io/voice_cloning_app/).

## Estado actual

| Elemento | Estado |
|---|---|
| Resumen Ejecutivo (2 págs, plantilla IEEE/RX) | Disponible en `docs/Resumen_Ejecutivo_VoiceCloning.pdf` |
| Memoria académica completa (LaTeX + PDF) | Pendiente — `TODO_VERIFICAR` |
| Documento de alcance del proyecto | Disponible internamente (`preproyectos/VOZ/Alcance_Proyecto_Voz.tex`) |
| Estudio SOTA + protocolo benchmark | Disponible internamente (`preproyectos/VOZ/estudio_voz_final.pdf`) |
| Resumen ejecutivo del benchmark (no público) | Disponible internamente (`voice_cloning/entregable/resumen_ejecutivo_2026-04-14.md`) |

## Estructura prevista

1. **Introducción** — Necesidad clínica (pacientes ORL con pérdida de voz), estado actual de la clonación de voz, posición del proyecto.
2. **Marco ético-jurídico** — RGPD art. 9, Ley IA UE 2024/1689 art. 50, consentimiento específico para clonación, base legal hospitalaria.
3. **Estado del arte** — Pipelines clásicos, codec LM, no-autorregresivos, flow matching/diffusion. Referencias: XTTS-v2, OpenVoice, CosyVoice 3, MaskGCT, VoiceCraft, VALL-E.
4. **Metodología de evaluación** — Decision gates, métricas (WER, UTMOS22, WavLM, ECAPA, AASIST, watermark detection), dataset VoxPopuli-ES, protocolo de escucha ciega.
5. **Resultados experimentales** — 528 generaciones, tabla comparativa, hallazgos overnight, exclusión de XTTS-v2 por CPML.
6. **Arquitectura del sistema** — Frontend Vue 3, backend FastAPI, workers nativos, postproceso, KMS, audit chain.
7. **Marco de salvaguardas** — Watermarking PerTh + AudioSeal, AASIST, audit log append-only, consentimiento específico, restricción contractual de usos.
8. **Discusión** — Limitaciones, riesgos residuales, comparación con literatura.
9. **Conclusión y trabajo futuro** — Fine-tuning con voz del paciente, escucha clínica ciega, integración con SISN2.

## Perfiles de lectura

| Audiencia | Capítulos prioritarios |
|---|---|
| Tribunal Premios Salut Innova | Resumen Ejecutivo · 1 · 2 · 7 · 9 |
| Comité de Ética Asistencial | 1 · 2 · 7 · 8 |
| Servicio Jurídico | 2 · 7 (apartado XTTS-v2 / CPML) · referencias regulatorias |
| Revisor técnico | 3 · 4 · 5 · 6 |
| Replicador externo | 4 · 5 · 6 + [[Reproducibilidad]] |

## Referencias bibliográficas clave

- **VALL-E / VALL-E 2** — Wang et al., Microsoft Research. Codec LM como marco conceptual.
- **CosyVoice 3** — Alibaba DAMO Academy. LLM + flow matching.
- **MaskGCT** — Non-autorregresivo masked codec.
- **XTTS-v2** — Coqui. Open-weight, licencia CPML restrictiva.
- **AASIST** — Jung et al. (2022). Audio anti-spoofing.
- **AudioSeal** — San Roman et al., Meta AI (2024). Watermarking neural.
- **PerTh** — Watermark perceptualmente imperceptible, embebido nativamente por Chatterbox.
- **Reglamento UE 2024/1689 (Ley IA)** — Artículos 9, 50.
- **Reglamento UE 2016/679 (RGPD)** — Artículo 9 sobre datos biométricos.
