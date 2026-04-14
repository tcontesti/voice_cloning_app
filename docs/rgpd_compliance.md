# Cumplimiento RGPD + Ley IA UE 2024/1689

Documento de referencia para el Delegado de Protección de Datos (DPD) y el
Comité de Ética Asistencial del Hospital Son Llatzer.

## Base jurídica del tratamiento

- Art. 9.2.h RGPD: tratamiento necesario para fines de asistencia sanitaria.
- Art. 9.2.a RGPD: consentimiento explícito adicional por tratarse de datos
  biométricos (la voz) con fines de identificación inequívoca.

## Categorías de datos

| Categoría                       | Tabla / ubicación           | Retención                  |
|---------------------------------|-----------------------------|----------------------------|
| Grabaciones de voz (biométrico) | MinIO cifrado SSE-C         | 90 días + borrado lógico   |
| Modelo vocal derivado           | No persistente en M5-M7     | —                          |
| Textos sintetizados             | `app.syntheses.text`        | Borrado con la síntesis    |
| Audios sintetizados             | MinIO cifrado SSE-C         | 90 días (config)           |
| Consentimientos                 | `app.consents` + hash chain | Indefinido (obligación)    |
| Registros de auditoría          | `audit.audit_log` (immutable)| ≥ 5 años (ENS Media)       |

No se guardan **embeddings** persistentes. El perfil de voz es una
**lista de IDs de grabaciones de referencia** — la re-síntesis re-extrae
el speaker embedding en tiempo real.

## Derechos ARSULIPO (RGPD arts. 15-22)

| Derecho           | Implementación actual                                         |
|-------------------|---------------------------------------------------------------|
| Acceso            | Endpoints `/recordings`, `/synthesis`, `/audit/logs` (auditor)|
| Rectificación     | Manual por admin (no hay datos "rectificables" en biometría)  |
| Supresión         | `DELETE /recordings/{id}` + purga programada 30 días después  |
| Limitación        | Flag `active` en usuario (bloquea login + workers)            |
| Portabilidad      | Export JSON de síntesis + descarga directa de WAVs propios    |
| Oposición         | Retirada del consentimiento + `active=false` al usuario       |

Toda acción de ejercicio de derechos queda registrada en `audit.audit_log`
con actor, timestamp, y motivo.

## Art. 50 Ley IA UE 2024/1689 — transparencia de IA generativa

### Obligaciones que cumplimos

1. **Identificación de contenido generado artificialmente**:
   - Todo WAV sintetizado lleva watermark (PerTh para Chatterbox, AudioSeal
     para OmniVoice/Qwen3).
   - La UI marca visualmente los audios con "Watermark verificado" y
     registra el resultado en la fila de síntesis (`watermark_verified`).
   - Si el watermark no se detecta tras síntesis, el job se marca como
     `failed` y se audita con nivel ERROR.

2. **Información al sujeto (paciente)** en el consentimiento
   (`app/consent_texts/v1-2026-04-14-DRAFT.md`):
   - Mención explícita de "deepfake audio" y de la marca técnica.
   - Enumeración de riesgos residuales.
   - Datos del DPD y procedimiento de reclamación AEPD.

3. **Supervisión humana**:
   - No hay uso autónomo. Cada generación requiere texto introducido por
     personal clínico o paciente supervisado.
   - Roles `clinico` y `admin` en workflow opcional de aprobación (M9+).

4. **Ausencia de prácticas prohibidas (art. 5)**:
   - No categorización biométrica sensible.
   - No reconocimiento emocional en contexto laboral/educativo.
   - No social scoring.

### No cumplidas aún — tracked

- [ ] Marca visual en el audio mismo además del watermark técnico
      (consideración UX; no exigido literalmente por el artículo).
- [ ] Canal de comunicación directo (botón "reportar mal uso") visible en
      cada descarga — planificado M9.
- [ ] Training del personal clínico antes del go-live — planificado M9.

## Evaluación de impacto (EIPD / DPIA)

Plantilla AEPD en preparación. Puntos críticos pre-identificados:

- Riesgo alto por categoría especial (biometría) → requiere EIPD previo.
- Riesgo de suplantación residual → mitigado por watermark + AASIST + audit.
- Riesgo de acceso no autorizado → mitigado por TLS + RBAC + SSE-C + audit
  hash chain.
- Riesgo de retención excesiva → mitigado por borrado lógico + purga 30 d.

La EIPD se firma antes del go-live clínico (no en MVP técnico).

## Puntos pendientes de validación jurídica

1. Texto exacto del consentimiento — actualmente LOREM marcado claramente.
2. Plazos de retención de grabaciones (propuesta 90 d; confirmar con DPD).
3. Dictamen sobre XTTS-v2 (CPML, actualmente excluido).
4. Autorización de la Comunidad Autónoma para biometría clínica.
5. Acuerdo de encargo de tratamiento interno (si se externalizase algún
   componente — no es el caso en M8, todo on-prem).
