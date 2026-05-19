# Colaboraciones

> [[Home]] · Colaboraciones

El proyecto cumple por construcción el criterio de **Cooperación UIB · IB-Salut (10 %)** de los Premios Salut Innova UIB-HLL Son Espases 2026. El equipo combina ingeniería y desarrollo desde la Universitat de les Illes Balears con liderazgo clínico desde el Hospital Universitario Son Llàtzer, en el marco del convenio UIB · IB-Salut · FUEIB.

## Equipo coautor

El proyecto está codesarrollado por cuatro coautores con responsabilidades complementarias y paritarias:

### Liderazgo clínico · Hospital Universitario Son Llàtzer (IB-Salut)

- **Dra. Amaya Roldán Fidalgo** — Facultativo Especialista de Área (FEA), Servicio de Otorrinolaringología y Cirugía de Cabeza y Cuello.

Responsabilidades clínicas:
- Definición de la población diana: pacientes con patología que amenaza la voz — cáncer de laringe, cirugía de cabeza y cuello, ELA, intubación prolongada, daño neurológico.
- Diseño del protocolo de captura de voz residual (frases controladas, condiciones acústicas, duración mínima).
- Criterios clínicos de aceptación perceptiva: inteligibilidad, similitud, ausencia de artefactos audibles.
- Supervisión del consentimiento informado específico para clonación, distinto del consentimiento de grabación.
- Coordinación con consultas de Logopedia, Rehabilitación y Cirugía Maxilofacial / Cabeza y Cuello.
- Planificación de la fase de escucha ciega clínica (pendiente de aprobación por Comité de Ética).

### Liderazgo técnico · UIB · Escola Politècnica Superior

- **Andrés Borrás Santos** — graduado en Ingeniería Informática (UIB · EPS).
- **Marc Link Cladera** — estudiante de Ingeniería Informática (UIB · EPS), defensa de TFG prevista para junio de 2026.
- **Antonio Contestí Coll** — estudiante de Ingeniería Informática (UIB · EPS), defensa de TFG prevista para junio de 2026; Técnico de Gestión de Sistemas y Tecnologías de las Telecomunicaciones, Hospital Universitario Son Llàtzer (IB-Salut). `toni.contesti.coll@gmail.com`.

Responsabilidades técnicas:
- Diseño de la arquitectura cliente-servidor (Vue 3, FastAPI, Celery, MinIO, Postgres, RabbitMQ, Redis, Vault).
- Implementación de los adaptadores de modelo (Chatterbox, OmniVoice, Qwen3-TTS, ElevenLabs).
- Postproceso watermark (PerTh + AudioSeal) y anti-spoofing (AASIST).
- Audit log append-only con cadena de hashes SHA-256 y endpoint de verificación.
- Benchmark reproducible: 528 generaciones, decision gates, hallazgos overnight.
- Empaquetado Docker Compose (PC + Spark) y Helm chart (Kubernetes).
- Observabilidad: Prometheus + Grafana + Loki.
- Pruebas de carga (Locust), pruebas unitarias (pytest), pruebas de UI manuales con CHECKLIST.

## Marco institucional · Convenio UIB · IB-Salut · FUEIB

El proyecto se desarrolla bajo el convenio entre la Universitat de les Illes Balears, el Servei de Salut de les Illes Balears (IB-Salut) y la Fundació Universitat-Empresa de les Illes Balears (FUEIB). Este convenio articula la incorporación de graduados de la EPS a proyectos asistenciales reales del HUSLL.

Beneficios concretos para el proyecto:
- Acceso a la infraestructura GPU compartida del hospital (DGX Spark GB10).
- Integración con el resto de proyectos de IA clínica (motor ICA de series temporales, detección de flebitis, dosificación antibiótica, detección de nódulos pulmonares CXR).
- Marco ético-jurídico compartido (Comité de Ética Asistencial, Servicio Jurídico, DPO).
- Soporte de la Subdirección de Innovación, Tecnología y Proyectos del HUSLL.

## Apoyo institucional y técnico (HUSLL)

- **Subdirección de Innovación, Tecnología y Proyectos** — gobierno del Comité de IA del HUSLL, validación de seguridad del paciente, definición de estrategia para modelos predictivos y generativos.
- **Servicio Jurídico HUSLL** — dictamen pendiente sobre licencia CPML de XTTS-v2.
- **Comité de Ética Asistencial** — aprobación pendiente del protocolo de escucha ciega para la fase de validación clínica.
- **Delegado de Protección de Datos** — `dpd@hsll.es`, contacto formal para el derecho del interesado.

## Referencias internacionales

El proyecto se apoya en el trabajo de referencia de:
- **AASIST** — Jung et al. (NAVER Clova) para anti-spoofing.
- **AudioSeal** — San Roman et al., Meta AI Research (2024) para watermark.
- **WavLM, ECAPA-TDNN** — Microsoft y SpeechBrain para evaluación de similitud de locutor.
- **VALL-E, MaskGCT, CosyVoice, XTTS** — como marco conceptual del estado del arte.

## Contacto

| Rol | Persona / canal |
|---|---|
| Coordinación técnica | Antonio Contestí Coll — `toni.contesti.coll@gmail.com` |
| Coordinación clínica | Dra. Amaya Roldán Fidalgo — Servicio de ORL, HUSLL |
| Delegado de Protección de Datos | `dpd@hsll.es` |
| Repositorio | <https://github.com/tcontesti/voice_cloning_app> |
| Landing | <https://tcontesti.github.io/voice_cloning_app/> |
| Wiki | <https://github.com/tcontesti/voice_cloning_app/wiki> |
