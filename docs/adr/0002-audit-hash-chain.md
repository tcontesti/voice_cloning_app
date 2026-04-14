# ADR 0002 — Audit log con hash chain SHA-256

**Fecha:** 2026-04-14
**Estado:** Aceptado

## Contexto

RGPD art. 30 + Ley IA UE 2024/1689 art. 12 exigen registro de actividad
inalterable y trazable. El hospital necesita poder demostrar a un inspector
que **ningún registro ha sido modificado o eliminado** desde su creación.

## Decisión

Tabla `audit.audit_log` append-only con hash chain SHA-256.

**Estructura por fila:**
- `id` BIGINT IDENTITY (orden de inserción)
- `actor_id`, `action`, `resource_type`, `resource_id`, `payload` JSONB
- `created_at` TIMESTAMPTZ (server_default `now()`)
- `prev_hash` CHAR(64) — hash de la fila anterior (génesis = 64 ceros)
- `hash` CHAR(64) UNIQUE — sha256 del canónico de esta fila

**Canónico:** `json.dumps({prev_hash, actor_id, action, resource_type, resource_id, payload, created_at}, sort_keys=True, separators=(",",":"))`. Cualquier modificación de cualquier campo rompe el hash.

**Defensa en profundidad:**
1. **Triggers DB** que bloquean UPDATE/DELETE sobre `audit.audit_log` con `RAISE EXCEPTION 'audit_log is append-only'`.
2. **Hash chain** que detecta tampering aunque el atacante consiga DB superuser y use `SET session_replication_role = replica` para saltar triggers.
3. **Advisory lock** Postgres (`pg_advisory_xact_lock(919191)`) en cada append serializa concurrencia y mantiene `prev_hash` consistente.
4. En prod (M8): el rol `vcapp` no tendrá GRANT UPDATE/DELETE — sólo INSERT y SELECT.

**Verificación:** `app.core.audit.verify_chain(rows)` recorre los rows en orden ascendente y devuelve `(ok, broken_id)` indicando dónde se rompió la cadena.

## Alternativas descartadas

- **Append-only log externo (Vector → S3 immutable bucket)**: más infra, latencia, separación de transaccionalidad con el resto.
- **Event store (EventStoreDB, Marten)**: overkill para escala de 5-100 pacientes/día.
- **Solo trigger sin chain**: detecta ataques desde el rol app, no desde DBA.
- **Solo chain sin trigger**: no detecta hasta `verify_chain`. Triggers fuerzan al atacante a usar privilegios elevados.
- **Merkle tree**: ventaja sólo si necesitas pruebas de inclusión parciales — aquí siempre verificamos toda la cadena. Coste de implementación no compensa.

## Consecuencias

- INSERT en `audit_log` cuesta una lectura adicional (tail) + advisory lock. Aceptable: <1 ms.
- Verificación de cadena es O(n). Para n=10^6 entradas (~10 años de uso a esta escala) es ~5s; suficiente para auditorías eventuales.
- El `payload` JSONB **no puede contener PII sensible** (texto sintetizado, embeddings, audio): por política, sólo metadatos + hashes. La capa de servicio es responsable de filtrar antes de `audit_svc.append()`.
- Cambiar el formato canónico rompe verificación retroactiva: si en algún momento se cambia, hay que migrar (re-hashear con marca explícita "v2").

## Verificación (M2)

Tests obligatorios — todos verdes en `tests/test_audit_chain.py`:

- `test_genesis_prev_hash` — primera fila enlaza a 64 ceros.
- `test_chain_links_consecutive_entries` — `row[i].prev_hash == row[i-1].hash`.
- `test_verify_chain_passes_on_clean_chain` — verificador OK con cadena limpia.
- `test_verify_chain_detects_payload_tampering` — saltando trigger con `session_replication_role=replica`, modificar payload de fila 3 → verifier devuelve `(False, row3.id)`.
- `test_append_only_trigger_blocks_update` / `_blocks_delete` — confirman el trigger.
- `test_appends_produce_unique_hashes` — 50 appends no colisionan.
