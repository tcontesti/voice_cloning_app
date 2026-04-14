# Security hardening — vcapp

Summary of security controls implemented and their current status.

## Authentication

| Control                                  | Dev         | Prod          |
|------------------------------------------|-------------|---------------|
| Identity provider                        | Mock OIDC   | Keycloak 26   |
| Token algorithm                          | HS256       | RS256 (JWKS)  |
| Token TTL                                | 8 h         | 8 h (config)  |
| WebSocket auth                           | ?token=jwt  | ?token=jwt    |
| JIT user provisioning from OIDC claims   | —           | Yes           |
| MFA                                      | No          | Keycloak policy (to enable) |

## Authorization

- RBAC with 4 roles: `paciente | clinico | admin | auditor`
- Endpoint-level guards via `require_roles(...)`
- Resource ownership checks in services (recordings/profiles/syntheses 404 for cross-user access)
- Router guards on the frontend mirror the backend checks (defense in depth, not authoritative)

## Secrets management

| Secret         | Dev                         | Prod                                  |
|----------------|-----------------------------|----------------------------------------|
| APP_SECRET_KEY | .env                        | SealedSecret / ExternalSecret         |
| DB passwords   | .env                        | Helm `auth.existingSecret`            |
| MinIO root     | .env                        | Helm `auth.existingSecret`            |
| KMS master     | .env (KMS_MOCK_KEY)         | Vault KV at `secret/data/vcapp/master`|
| Vault token    | .env (dev root)             | Vault Agent Injector (short-lived)    |

- `.env.example` ships only placeholders.
- `.gitignore` excludes `.env`, `.env.local`, nginx certs.

## Transport

- Dev: self-signed TLS at nginx (`infra/nginx/certs/`).
- Prod: Ingress TLS with cert from internal CA or ACME; forced HTTPS redirect.
- HSTS, CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy all set.

## Data-at-rest

- Postgres + MinIO run on encrypted volumes in prod (LUKS or vendor-managed).
- MinIO adds **SSE-C per object** with per-object DEK derived as
  `HMAC-SHA256(master_key, s3_key)`. Master key from Vault (prod) /
  env (dev). See ADR 0003.
- Audit log has application-level hash chain + DB triggers blocking
  UPDATE/DELETE. See ADR 0002.

## Input validation

- Audio uploads: 25 MB cap, WAV only, SNR ≥ 15 dB, speech_ratio ≥ 0.30,
  duration ∈ [1, 60] s, supported sample rates only.
- Synthesis text: 500 chars max, printable/newline/tab only, text NEVER
  written to audit log (only length + metadata).
- Email: RFC-syntactic validation (no disposable-TLDs reserved like .local).

## Supply chain

- Pinned dependency ranges in `pyproject.toml` and `package.json`.
- ARM64 wheels only when available; `webrtcvad-wheels` chosen for ARM64.
- `torch==2.11.0+cu130` pinned; `worker/install_into_venv.sh` verifies torch
  wasn't downgraded after adding celery/redis/minio etc.
- Docker base images pinned by digest in prod (TODO for `infra/helm/vcapp`).

## Audit & compliance

- Append-only audit log with SHA-256 hash chain (see ADR 0002).
- Every mutating endpoint writes an audit entry with metadata only
  (no PII in payloads).
- Consent text versioned in git; sha256 of the exact text the user saw is
  stored at signature time. Drift → 409 re-read required.
- AudioSeal or PerTh watermark verified on every synthesis; missing watermark
  = job marked failed and logged at ERROR. See ADR 0005/0006.
- AASIST anti-spoofing score stored per synthesis.

## Known gaps — tracked

- [ ] MFA on clinical roles (Keycloak policy)
- [ ] Vault HA cluster (instead of single dev-mode pod)
- [ ] Rate limiting per user (stub: 60 req/min / 10 syntheses/h) — needs
      middleware with Redis backend
- [ ] Playwright e2e browser tests (tracked for M9)
- [ ] Supply-chain attestation (SBOM + Cosign sign)
- [ ] Penetration test (scheduled post-MVP with hospital security team)

## Compliance mapping

- **RGPD**: ADR 0002 (audit), consent flow (M2), SSE-C + Vault, soft-delete + retention
- **Ley IA UE 2024/1689 art. 50**: consent mentions synthetic audio + watermark,
  audit trail per generation, identification via watermark
- **ENS** (Esquema Nacional de Seguridad): maps to Media category — controls
  listed above; formal ENS statement pending hospital Servicio de
  Seguridad Informática review.
