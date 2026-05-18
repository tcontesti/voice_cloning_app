# Experimentos

> [[Home]] · Experimentos

Mapa del trabajo experimental previo a la integración de modelos en la aplicación clínica. La selección de los tres modelos activos (Chatterbox, OmniVoice, Qwen3-TTS) y la exclusión de XTTS-v2 se justifican con un benchmark reproducible documentado a continuación.

## Diseño experimental

| Dimensión | Valores | Total |
|---|---|---|
| Modelos | Chatterbox, OmniVoice, Qwen3-TTS, XTTS-v2 | 4 |
| Locutores | 2 masculinos + 2 femeninos (VoxPopuli-ES) | 4 |
| Longitudes de referencia | 3 s, 10 s, 30 s | 3 |
| Frases de prueba | Hospital + cotidianas, longitudes variables | 11 |
| **Generaciones totales** | 4 × 4 × 3 × 11 | **528** |
| Tasa de fallo | 0 % |

## Métricas

| Métrica | Herramienta | Qué mide |
|---|---|---|
| WER / CER | faster-whisper large-v3 (ES) | Inteligibilidad |
| MOS UTMOS22 | tarepan/SpeechMOS · utmos22_strong | Naturalidad de referencia |
| MOS wvmos | wav2vec2 MOS predictor | Naturalidad (proxy) |
| Similitud WavLM | microsoft/wavlm-large | Preservación de identidad (primaria) |
| Similitud ECAPA-TDNN | speechbrain/spkrec-ecapa-voxceleb | Preservación de identidad (baseline) |
| AASIST anti-spoofing | clovaai/aasist | Probabilidad SPOOF (mayor = más detectable) |
| Watermark PerTh | resemble-perth | Verificación del WM nativo |
| Watermark AudioSeal | facebookresearch/audioseal | Verificación del WM post-hoc |
| RTF / TTFA / VRAM | Medición directa | Viabilidad operativa |

## Decision gates (ajustados tras overnight 2026-04-13/14)

| Gate | Umbral | Justificación |
|---|---|---|
| WER | < 8 % | Inteligibilidad clínica suficiente |
| MOS UTMOS22 | ≥ 3.5 | Bajado desde 3.8 tras observar que UTMOS real es ~0.5-0.8 pts más estricto que wvmos |
| Sim WavLM | > 0.75 | Bajado desde 0.80 tras observar margen real de zero-shot en castellano |
| TTFA | < 3 s | Aceptable para uso clínico interactivo |
| Licencia | MIT / Apache 2.0 / MPL | Compatibilidad hospital público |
| Tasa de fallo | < 5 % | Robustez operativa |

## Resultados (overnight 2026-04-14)

| Modelo | Licencia | WER | UTMOS | Sim WavLM | Sim ECAPA | AASIST | PerTh WM | RTF | TTFA | VRAM |
|---|---|---|---|---|---|---|---|---|---|---|
| **Chatterbox** | **MIT** | **8.0 %** | **3.11** | 0.707 | 0.661 | 0.471 | **✅ 132/132** | 0.50 | 3.2 s | 3.6 GB |
| **OmniVoice** | **Apache 2.0** | 10.9 % | 2.67 | **0.787** | **0.756** | 0.503 | ❌ | 1.27 | 5.8 s | 4.0 GB |
| **Qwen3-TTS** | **Apache 2.0** | 8.6 % | **3.11** | 0.775 | 0.716 | 0.629 | ❌ | 1.07 | 6.3 s | 3.6 GB |
| **XTTS-v2** | CPML | 8.9 % | 2.60 | 0.670 | 0.605 | 0.053 | ❌ | **0.22** | **1.7 s** | **1.96 GB** |

## Hallazgos clave

1. **Qwen3-TTS desbloqueado y competitivo.** Tras resolver la incompatibilidad `transformers 5.5` con un venv aislado, Qwen3-TTS iguala a Chatterbox en calidad audible (UTMOS 3.11) y supera su similitud de locutor (WavLM 0.775 vs 0.707).
2. **UTMOS real es más estricto que wvmos.** Los *gates* iniciales (MOS ≥ 3.8) son inalcanzables en zero-shot castellano sin fine-tuning. Se ajusta a 3.5 para esta fase.
3. **Anti-spoofing AASIST revela riesgo en XTTS-v2.** Score 0.053 — pasa por humano casi siempre. Los demás modelos (0.47–0.63) son claramente detectables como sintéticos, lo cual es deseable: añade una barrera adicional frente a uso malicioso.
4. **Watermarking nativo solo en Chatterbox.** PerTh detector confirma 132/132 WAVs marcados. Los otros modelos requieren AudioSeal post-hoc obligatorio en producción.
5. **CosyVoice 3 descartado.** API 2026 incompatible con el adaptador actual. Pendiente reintentar con constructor nuevo en futuras rondas.

## Conclusiones operativas

- **Modelo A (por defecto): Chatterbox** — MIT, watermark nativo, real-time (RTF 0.50), MOS decente.
- **Modelo B: OmniVoice** — Apache 2.0, mejor identidad vocal, requiere AudioSeal post-hoc y no es real-time.
- **Segundo candidato: Qwen3-TTS** — Apache 2.0, calidad similar a Chatterbox y mejor similitud; requiere venv aislado.
- **Excluido: XTTS-v2** — bloqueo dual por licencia CPML y por AASIST ínfimo.

Ningún modelo supera todos los gates simultáneamente. La decisión final entre A y B (o uso combinado) debe apoyarse en **evaluación humana** con escucha ciega clínica (Fase 6 de la hoja de ruta), cuyo protocolo está documentado pero pendiente de aprobación por Comité de Ética.

## Reproducibilidad

Pipeline de evaluación previo en `voice_cloning/` (repositorio interno de experimentos, no público). Scripts orquestados con MLflow. Salidas crudas en `results/benchmark_final_v2.csv` (528 filas) y `results/security_eval_v2.csv`. La replicación dentro de esta aplicación requiere:

1. DGX Spark con CUDA 13.0, 130 GB VRAM unificada.
2. Datasets VoxPopuli-ES + 11 frases de prueba (no se redistribuyen).
3. Pesos de los 4 modelos descargados según sus licencias originales.
4. Métricas: faster-whisper large-v3, WavLM-large, ECAPA-TDNN, AASIST, resemble-perth, audioseal.

Ver [[Reproducibilidad]] para el escenario "evaluar un modelo".
