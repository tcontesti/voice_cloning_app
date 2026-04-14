# Deployment — Hospital Son Llatzer (on-prem)

## Topology

```
                        ┌────────────────────────────────────┐
                        │   Kubernetes cluster (Spark NUCs)  │
        users ──HTTPS──►│                                    │
                        │  Ingress (nginx) ──► frontend      │
                        │           └──► backend (API + WS)  │
                        │                   │ │              │
                        │         postgres ─┘ │              │
                        │         redis ──────┘              │
                        │         rabbitmq  minio (TLS)      │
                        └─────────────┬──────────────────────┘
                                      │ RabbitMQ / Redis
                         ┌────────────▼──────────────┐
                         │   DGX Spark (GPU host)    │
                         │  systemd --user workers:  │
                         │    worker_chatterbox      │
                         │    worker_omnivoice       │
                         │    worker_qwen3           │
                         │  (each uses native venv)  │
                         └───────────────────────────┘

                         ┌───────────────────────────┐
                         │   Keycloak (sso.hsll.es)  │
                         │   Vault    (vault.hsll.es)│
                         └───────────────────────────┘
```

Workers stay **on the Spark host**, not in k8s — GPU + native venv + existing
model checkpoints under `~/voice_cloning/models/`. See `worker/README.md`.

## Helm install

```bash
# Add required sub-chart repos
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm dependency update infra/helm/vcapp

# Create secrets out-of-band (SealedSecrets or ExternalSecrets recommended)
kubectl create secret generic vcapp-secrets \
    --from-literal=APP_SECRET_KEY="$(openssl rand -base64 48)" \
    --from-literal=POSTGRES_USER=vcapp \
    --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 24)" \
    --from-literal=POSTGRES_DB=vcapp \
    --from-literal=REDIS_PASSWORD="$(openssl rand -base64 24)" \
    --from-literal=RABBITMQ_USER=vcapp \
    --from-literal=RABBITMQ_PASSWORD="$(openssl rand -base64 24)" \
    --from-literal=MINIO_ROOT_USER=vcapp \
    --from-literal=MINIO_ROOT_PASSWORD="$(openssl rand -base64 24)" \
    --from-literal=VAULT_TOKEN="$(cat /vault-agent/token)"

# Install
helm install vcapp infra/helm/vcapp \
    --namespace vcapp --create-namespace \
    --values infra/helm/vcapp/values.yaml \
    --values infra/helm/vcapp/values.prod.yaml   # hospital-specific overrides
```

## First-time bootstrap

1. Keycloak: import `infra/keycloak/realm-vcapp.json` into `sso.hsll.es`
   (replace placeholder users with real hospital SSO accounts, or set up
   LDAP federation).
2. Vault: create transit key + KV secret:
   ```bash
   vault secrets enable -path=secret kv-v2
   vault kv put secret/vcapp/master key="$(openssl rand -base64 32)"
   # Policy for the app token
   cat <<EOF | vault policy write vcapp-read -
   path "secret/data/vcapp/*" { capabilities = ["read"] }
   EOF
   ```
3. MinIO: pre-create buckets `recordings`, `syntheses` with versioning on
   and object-lock for audit-critical objects (future M9).
4. Apply Alembic migrations:
   ```bash
   kubectl -n vcapp exec deploy/vcapp-vcapp-backend -- alembic upgrade head
   ```
5. Deploy Spark workers (see worker/README.md §systemd).

## Config matrix — dev vs prod

| Variable              | dev (compose)           | prod (Helm)               |
|-----------------------|-------------------------|---------------------------|
| `AUTH_MODE`           | `mock`                  | `keycloak`                |
| `KMS_MODE`            | `mock`                  | `vault`                   |
| `STORAGE_ENCRYPTION`  | `none`                  | `sse-c` (TLS MinIO)       |
| `MINIO_SECURE`        | `false`                 | `true`                    |
| `APP_SECRET_KEY`      | hardcoded in `.env`     | sealed secret             |

## Observability

Kube-prometheus-stack is expected in-cluster. The backend emits Prometheus
metrics at `/metrics`. Set `serviceMonitor.enabled=true` (default).

Key metrics:
- `vcapp_requests_total` — per-path request counter
- RabbitMQ queue depth (via built-in prometheus plugin port 15692)
- Postgres via `postgres-exporter`
- Redis via `redis-exporter`
- GPU via `nvidia-dcgm-exporter` (Spark-side; scraped by central Prometheus
  if network allows, else via a separate prom on the Spark host)

## Backups

- **Postgres**: `pg_dump` nightly to MinIO bucket `backups` + WAL archiving.
- **MinIO**: `mc mirror` with versioning + external tape/S3 cold copy.
- **Vault**: Raft snapshots weekly, stored on tape.
- **Keycloak realm**: `kc.sh export` nightly.

See `scripts/backup_db.sh` (stub — M9 finishes with a tested restore runbook).

## Disaster recovery runbook

Minimal RTO target: 4 h. See `docs/dr-runbook.md` (to be written with the
hospital SRE team post-MVP).

## Smoke checklist after deploy

```bash
curl -fsS https://vcapp.hsll.es/api/health
curl -fsS https://vcapp.hsll.es/api/synthesis/models
# Login via Keycloak, upload reference, synthesize 1 sample end-to-end
```
