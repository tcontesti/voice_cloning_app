# ADR 0008 — Prod-readiness: Keycloak + Vault + observability + Helm

**Fecha:** 2026-04-14
**Estado:** Aceptado

## Decisiones

### AUTH_MODE=mock|keycloak toggle, no branch

En lugar de reemplazar el mock OIDC, el backend acepta ambos modos vía la
env var `AUTH_MODE`. Razones:

- Dev-standalone sigue funcionando sin levantar Keycloak (pesado, ~45 s de
  warmup en la Spark).
- Smoke tests en CI no dependen de infra externa.
- Migración del hospital: se puede empezar con `mock` para integración
  técnica y cambiar a `keycloak` cuando el SSO esté listo sin redeploy.

`decode_token()` en `app/core/security.py` hace la ramificación:
- `mock` → HS256 con APP_SECRET_KEY (como en M2)
- `keycloak` → RS256 verificado contra JWKS de Keycloak (cache 1 h, refetch
  en kid miss para tolerar rotación)

JIT provisioning: primera vez que Keycloak envía un token válido, el
backend crea un row en `app.users` con el rol inferido de
`realm_access.roles`. Mapeo: admin > auditor > clinico > paciente
(elige el más privilegiado encontrado).

### KMS_MODE=mock|vault toggle, mismo patrón

`_master_key()` tiene ambas implementaciones cacheadas. Vault se consulta
en KV v2 en `secret/data/vcapp/master`. El formato del secret es
`{"key": "<base64 de 32+ bytes>"}` — el **mismo** formato que `KMS_MOCK_KEY`.

Consecuencia importante: **migrar de mock a vault no re-cifra datos** si
se pone el mismo valor base64 en ambos. `scripts/vault_bootstrap.sh` lo
escribe tal cual desde la env, así dev/prod producen DEKs idénticas para
el mismo `s3_key`. (En prod real, se rota antes de go-live y se re-cifra.)

### Observability stack opt-in

`infra/docker-compose.observability.yml` se activa con `make observe`.
Separado porque los 4 contenedores adicionales (prom, grafana, loki,
promtail) + 2 exporters ocupan RAM/CPU significativos en dev.

En prod se asume kube-prometheus-stack pre-existente; el chart Helm expone
un ServiceMonitor (no despliega Prometheus).

Métricas emitidas por el backend vía `prometheus_client`:
`vcapp_requests_total{path=...}`. Añadir más counters es trivial en
`app/main.py`.

Dashboard inicial (`vcapp-overview.json`) deliberadamente mínimo: 4 paneles
Prometheus + 1 panel Loki de logs del backend. Más paneles se añaden según
dolores reales, no anticipadamente.

### Workers NO se orquestan con Helm

Explícito en `values.yaml` (`workers.deployInCluster: false`). Los workers
viven en la Spark (GPU + venvs existentes). Razonamiento completo en
ADR 0005; Helm sólo despliega lo stateless (API + frontend + deps).

Esto implica que la topología de producción tiene **2 planos**:
- Kubernetes con API/DB/queue/object store
- Spark host con workers conectados vía SSH tunnel / VPN interna

El mismo patrón se usa para MedGemma y DermApixel en el hospital — decisión
coherente.

### Helm chart: mínimo funcional, no gold-plated

El chart despliega:
- Deployments para backend + frontend con security contexts estrictos
  (runAsNonRoot, readOnlyRootFilesystem, drop ALL caps)
- Services ClusterIP
- Ingress con TLS + WebSocket routing (body-size 25M, read/send-timeout 1h)
- ServiceMonitor opcional para kube-prometheus-stack
- Sub-charts de Bitnami para postgres/redis/rabbitmq/minio (opt-in)

NO incluye:
- PodDisruptionBudget — pendiente cuando llegue HA
- NetworkPolicy — pendiente cuando se haga el threat-modelling con SRE
- HPA — fuera de scope MVP (escala 5-100 pacientes/día)
- Cert-manager Issuer — asumido pre-existente en el cluster

### Locust scenarios realistas, no sintéticos

Peso 8 paciente / 1 auditor / 1 health-check refleja la mezcla real esperada.
No se testea RTF de síntesis porque eso es un benchmark de worker (vive en
el repo original `voice_cloning/scripts/run_benchmark.py`).

Target MVP: p95 < 500 ms para endpoints API, sin 5xx a 50 VUs.

## Alternativas descartadas

- **Reemplazar mock por Keycloak directamente**: rompe CI y dev-standalone.
- **Vault en el mismo cluster que vcapp**: mala separación de dominios de
  seguridad. Vault es infraestructura transversal del hospital.
- **Grafana Cloud / Datadog**: SaaS no cumple on-prem.
- **Helm con Prometheus Operator embebido**: colisiona con el
  kube-prometheus-stack que ya usan otros proyectos del hospital.
- **Pulumi / Terraform en lugar de Helm**: Helm es el estándar k8s y menos
  curva de aprendizaje para el equipo SRE.

## Verificación

- Backend tests 61/61 pasan (sin regresiones tras añadir oidc/vault)
- `helm lint` del chart pasa (ver `make helm-lint` post-deploy)
- Observability + Keycloak + Vault validados manualmente con `make full`
  (los containers arrancan, Grafana ve los datasources, Keycloak importa
  el realm, Vault responde)

## Pendientes M9+

- MFA en Keycloak para roles clínicos
- Playwright e2e contra el stack completo
- DR runbook con el equipo SRE del hospital
- EIPD formal para el DPD
- Penetration test externo
- SBOM + Cosign signing de imágenes
- NetworkPolicy + PodSecurityPolicy / Pod Security Admission
- Training del personal clínico pre-go-live
