# Summary — PC-side medium fixes + Spark-coord notes

Resultado de la segunda tanda de la revisión (medios 10-17 + 3 ítems que
el Claude del Spark mandó al PC). Rama `main`, commits atómicos, tests
verdes al final.

## Commits landed (orden cronológico)

| # | Hash | Alcance |
|---|------|---------|
| #10 | `cf79471` | `fix(consent)` cancelar redirect setTimeout en unmount |
| #11 | `1818707` | `fix(auth)` quitar `bootstrapFromStorage` duplicado en App.vue |
| #12 | — | **Falso positivo** — `disabled` ya short-circuita en `Knob.vue:78` y `Fader.vue:69`. Sin commit. |
| #13 | `171aead` | `fix(ui)` SpectrumAnalyzer reschedula rAF si `getContext` devuelve null |
| #14 | `465e792` | `i18n` extracción de strings en `SystemStatusBadge`, `JobMonitor`, `RecorderStudio`, `SynthesizeView` |
| #15 | `37fa7c7` | `fix(scripts)` dev_stop filtra por puertos específicos del túnel |
| #16 | `5772ff5` | `fix(alembic)` `create_index if_not_exists=True` en 0001/0002/0003 |
| PC-A | `9b010d0` | `fix(autossh)` ServerAliveInterval 15→30 |
| PC-B | `06b1c4d` | `docs(resilience)` warning sobre dependencia de Redis :6380 |
| PC-C | (este doc) | análisis — sin cambios de código |

Tests frontend `vitest run` → 10/10. Tests backend `pytest` → 76/76 (última
ejecución antes de la tanda; no hay cambios en código backend aparte de
alembic y esos no ejecutan tests). Build `vite build` OK.

---

## PC-C — análisis: mover Celery result backend al Redis local de la Spark

**Pregunta del Claude del Spark**: ¿merece la pena mover el `result_backend`
de Celery a un Redis que corra en la propia Spark, para eliminar la
dependencia del reverse tunnel `-R 6380`?

### 1. ¿Qué del backend PC hace `.get()` sobre AsyncResult?

**Nada.** Grep exhaustivo:

```
grep -rn "result_backend\|AsyncResult\|\.result\b\|\.ready()" backend/ --include='*.py'
  # → zero matches in backend/app/ (solo texto en comentarios)

grep -rn "celery" backend/app/ --include='*.py'
  # → uso del celery_app:
  #   backend/app/api/synthesis.py:78     celery_app.send_task(...)   (fire-and-forget)
  #   backend/app/api/system.py:93        celery_app.control.inspect()  (usa broker, no backend)
  #   backend/app/workers/tasks.py         shared_task + progress.emit (worker-side)
```

- **El API del PC nunca lee el `result_backend`.** Sólo despacha tareas
  (`send_task`) y consulta el **broker** RabbitMQ para inspección de
  colas (`/system/health`).
- **El seguimiento de progreso NO usa result_backend**. Va por
  Redis pub/sub (canal `progress:job:<id>`) publicado desde
  `backend/app/workers/progress.py` y consumido por
  `backend/app/api/ws_jobs.py`.
- El result_backend sólo lo usa Celery internamente para persistir el
  `return dict(...)` de `synthesize()`. Esa persistencia es un side-effect
  del framework; nadie la consulta.

### 2. Qué pasa si se migra

**Propuesta del Spark**: `_BACKEND = "redis://localhost:6379/1"` en el
worker apuntando al Redis que montarían en la Spark; el PC sigue con su
Redis local para pub/sub y Celery en el PC usa `backend=None` o un
backend separado.

**Impacto real**:

- ✅ El `-R 6380` deja de ser crítico para *completar* una task. Una task
  puede retornar incluso si la tunnel cae durante el `return`, porque el
  write del dict va al Redis de la Spark.
- ⚠️ **No elimina la dependencia del `-R 6380` para progreso**. El
  canal pub/sub `progress:job:<id>` lo publica el worker sobre
  `s.redis_host:s.redis_port` que resuelve al Redis del PC vía el
  mismo reverse tunnel. Si cae `-R 6380`, la UI sigue sin ver progreso
  aunque la task acabe bien en Spark. Se necesitaría *también* mover
  pub/sub al broker de RabbitMQ (o a un Redis-pc2spark aparte) para
  eliminar la dependencia.
- ⚠️ `-R 5433` (Postgres) sigue siendo crítico: `tasks.py` hace
  `db.commit()` de `syn.status=succeeded` directamente contra Postgres
  del PC. Ése es el bottleneck real de "jobs stuck in queued" cuando
  la tunnel cae tras aceptar la task.
- ⚠️ Si en el futuro añadimos algo como admin UI con `AsyncResult.get()`
  para reintentar, cancelar o ver estado interno de Celery, ambos
  lados tendrían que volver a compartir result_backend. La migración
  nos bloquearía esa feature sin reconfigurar el cluster.

### 3. Recomendación

**No migrar ahora.** Argumentos:

1. El síntoma original que motivó la pregunta (jobs en `queued` tras drop
   de túnel) **no lo resuelve**. El culprit real es `-R 5433`
   (Postgres) porque el worker no puede escribir `status=succeeded`.
   Migrar sólo el result_backend deja ese bug intacto.
2. Actualmente el result_backend es coste puro (3 ms por task-complete
   write) sin lector. Moverlo es trabajo sin beneficio operativo medible.
3. Perdemos opcionalidad para features futuras basadas en `AsyncResult`.
4. El fix real ya está documentado (`docs/dev_multihost.md` sección
   "Dependencia crítica del reverse-tunnel Redis"): recuperación manual +
   `sshd ClientAliveInterval 30` en Spark. Y `ServerAliveInterval 30` en
   autossh (PC-A) ya alinea los timeouts.

**Si el escenario cambia** (por ejemplo: la Spark va a estar permanentemente
ligada a una red que hace NAT por horas, y no podemos reiniciar el túnel
manualmente):

- Paso 1: mover **pub/sub** a un canal de RabbitMQ (custom exchange
  `progress.*`). Quita la dependencia de `-R 6380` para visibilidad
  de progreso — y es compatible con nuestro broker ya tunneled forward.
- Paso 2: cambiar `commit(syn.status=succeeded)` desde el worker por un
  mensaje final al broker que el API consume y persiste. Quita `-R 5433`.
  El API se convierte en dueño único de la DB (cleaner para el piloto
  clínico).
- Paso 3 (opcional): result_backend en Spark-local. Ya sería cosmético.

Ese refactor es ~2 días de trabajo y un cambio de arquitectura
deliberado. No lo hagamos bajo la presión de un bug operativo
recuperable.

---

## Cosas que quedan fuera de esta tanda

- Tests específicos para `ws_jobs` (pool + shutdown). El pool tiene
  cobertura manual (`_get_pool()` smoke en la sesión anterior), pero no
  test automático. Fase 2.
- Admin/AuditLog views — sólo tienen tokens+tipografía. El tratamiento
  detallado "terminal mono + hash chain colorizado" del brief original
  sigue pendiente (ya trackeado en `docs/design_system.md`).
- i18n **en-GB** / **ca-ES**: las keys ya están estructuradas para
  admitirlo, falta sólo el archivo de traducción. Sin plan de entrega.

---

## Próximo paso sugerido

1. Tag intermedio opcional: `git tag v0.3.1-medium` (no esencial).
2. Ejecutar el Paso 5 del smoke de resiliencia (reconexión autossh tras
   restart sshd en Spark) ahora que `ServerAliveInterval` va a 30s y
   Spark debería responder con `ClientAliveInterval 30` (verificar).
3. Sincronizar con la sesión Claude del Spark si quedan recomendaciones
   cruzadas que no hayan pasado por aquí.
