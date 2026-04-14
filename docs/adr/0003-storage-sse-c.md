# ADR 0003 — Storage SSE-C con DEK derivada por objeto

**Fecha:** 2026-04-14
**Estado:** Aceptado (parcial — ver §Pendientes)

## Contexto

Las grabaciones de voz son **dato biométrico de categoría especial** (RGPD art. 9). Almacenarlas en MinIO sin cifrado en reposo no cumple el principio de integridad y confidencialidad (art. 5.1.f) ni el control técnico que exigirá el dictamen del DPD.

MinIO ofrece tres modos de cifrado server-side:
- **SSE-S3**: clave gestionada por MinIO (KMS interno, rotación opaca).
- **SSE-KMS**: clave de un KMS externo (Vault transit, AWS KMS).
- **SSE-C**: el cliente provee la clave en cada PUT/GET; MinIO no la persiste.

## Decisión

Adoptamos **SSE-C con DEK derivada por objeto** = `HMAC-SHA256(master_key, s3_key)`.

- **Master key** vive en KMS:
  - **Dev**: env `KMS_MOCK_KEY` (base64, 32 bytes mínimo). `KMS_MODE=mock`.
  - **Prod (M8)**: Vault transit. Rotación cada 90 días. Issue ya abierto en roadmap del hospital.
- **Derivación HMAC** evita persistir DEK por objeto (recuperar el master basta para recuperar todo).
- Sólo la API backend conoce el master → MinIO no puede leer los objetos por sí mismo (defense-in-depth contra incidente de credenciales MinIO).

### Para descargas

SSE-C requiere reenviar la clave en cada GET. Por eso **no se puede usar URL pre-firmada simple** para servir audio cifrado al cliente — la API **siempre** intermedia las descargas SSE-C, fetcheando con la DEK derivada y devolviendo el byte stream.

URLs pre-firmadas se reservan para artefactos sintetizados (M5+) que llevan watermark y pueden ir sin SSE-C, o para los WAVs sintetizados expuestos al paciente bajo flujo controlado.

## Limitación dev: HTTPS obligatorio para SSE-C

MinIO rechaza SSE-C sobre HTTP plano:

```
InvalidRequest: Requests specifying Server Side Encryption with
Customer provided keys must be made over a secure connection.
```

Por eso introducimos `STORAGE_ENCRYPTION` (env):
- `none` (dev local con `MINIO_SECURE=false`): objetos sin cifrar en reposo.
- `sse-c` (prod): activa SSE-C + requiere `MINIO_SECURE=true` (TLS en MinIO).

Esto es deuda controlada — el dev local trabaja sin cifrado, **prohibido** desplegar con `STORAGE_ENCRYPTION=none`. M8 añadirá:

1. TLS en MinIO (mismo cert pattern que nginx).
2. Health check arranque que falle si `APP_ENV=prod` y `STORAGE_ENCRYPTION != "sse-c"`.
3. Vault transit como `KMS_MODE=vault`.

## Alternativas descartadas

- **SSE-S3**: MinIO solo descifra para clientes autenticados con su API. Si el atacante consigue credenciales MinIO, lee todo en claro. No cumple el control de "el storage no debe poder leer los datos".
- **SSE-KMS**: equivalente funcional a SSE-C cuando el KMS está separado, pero MinIO sigue siendo intermediario. SSE-C nos da control directo del material criptográfico.
- **Cifrado client-side puro** (cifrar antes de subir): perdemos compactación, dedup por hash deja de funcionar (cada cifrado distinto), y nos ata a un esquema custom. SSE-C es el balance correcto.

## Consecuencias

- Reads SSE-C no son cacheables por proxy ni CDN: el byte stream pasa siempre por la API.
- Coste: una llamada HMAC + headers SSE-C extra por objeto (~µs).
- Si el master key se pierde, **los datos son irrecuperables**. Vault prod debe tener replicación + backup encriptado.
- Migración de master key futura: hay que re-cifrar todos los objetos con la nueva DEK derivada (script offline, M8 incluye design).

## Verificación (M3)

- `storage.derive_dek(key)` produce 32 bytes deterministas.
- Tests E2E `tests/test_recordings.py` ejercitan put/get sobre MinIO real con `STORAGE_ENCRYPTION=none` (dev). Tests de cifrado real esperan a M8 cuando MinIO tenga TLS local.

## Pendientes (issues abiertos)

- [ ] M8: TLS en MinIO + activar SSE-C en prod.
- [ ] M8: integración Vault transit (`KMS_MODE=vault`).
- [ ] M8: health check `APP_ENV=prod ⇒ STORAGE_ENCRYPTION=sse-c`.
- [ ] M8+: rotación de master key cada 90 días + script de re-cifrado.
