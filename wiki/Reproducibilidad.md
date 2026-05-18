# Reproducibilidad

> [[Home]] · Reproducibilidad

Cuatro escenarios prácticos para que un revisor externo (técnico, clínico o jurídico) pueda inspeccionar, ejecutar o ampliar el trabajo. Los escenarios suponen acceso a una máquina con Docker y, para los que tocan modelos, una GPU NVIDIA con CUDA 12.4+.

---

## Escenario A · Arrancar la aplicación en local

**Objetivo:** levantar la aplicación completa (backend + frontend + infra) en un único host.

```bash
git clone https://github.com/tcontesti/voice_cloning_app.git
cd voice_cloning_app

# Certificados TLS self-signed para nginx
openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout infra/nginx/certs/server.key \
    -out infra/nginx/certs/server.crt \
    -days 365 -subj "/CN=localhost"

make env        # crea .env desde .env.example (edita los CHANGE_ME_*)
make up         # levanta postgres + redis + rabbitmq + minio + backend + nginx
make ps         # comprueba healthchecks
curl -fsS http://localhost:8000/health
```

Para frontend (en otra terminal):

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Apertura:
- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- MinIO console: `http://localhost:9001`
- RabbitMQ management: `http://localhost:15672`

---

## Escenario B · Generar una síntesis end-to-end

**Objetivo:** verificar el pipeline completo (auth → upload → profile → synthesis → watermark → AASIST).

Requiere un worker corriendo en una GPU compatible. Si no tienes GPU local, puedes desplegar el backend en local y los workers en una Spark vía túnel SSH (ver `docs/dev_multihost.md`).

```bash
# 1) Workers natively on Spark (one model)
ssh SPARK_USER@SPARK_HOST
cd ~/voice_cloning_app
bash worker/install_into_venv.sh      # idempotente
bash worker/start_worker.sh chatterbox

# 2) Smoke end-to-end (en el backend host)
~/voice_cloning_env/.venv/bin/python worker/smoke_enqueue.py \
    --model chatterbox \
    --text "Hola, prueba clínica." \
    --ref  /home/SPARK_USER/voice_cloning/datasets/reference_clips/spk01_male_10s.wav
```

El script `smoke_enqueue.py`:
1. Sube el WAV de referencia a MinIO y crea su sha256.
2. Crea un usuario, un recording y un voice_profile en Postgres.
3. Inserta `synthesis (status=queued)` y publica a la cola del modelo.
4. Polling cada 2 s del estado hasta `done` / `error`.
5. Verifica `watermark_verified=true` y `aasist_score`.

---

## Escenario C · Reproducir el benchmark (528 generaciones)

**Objetivo:** evaluar un modelo (Chatterbox / OmniVoice / Qwen3-TTS) con métricas honestas y datos crudos exportables.

> Nota: el pipeline de benchmark vive en un repositorio interno (`voice_cloning/`) no publicado. Esta guía describe la replicación de su lógica con scripts equivalentes.

Pasos:
1. Descargar 4 locutores VoxPopuli-ES (2M + 2F). No se redistribuyen aquí; usar el dataset oficial.
2. Definir 11 frases de prueba (`benchmark/phrases.es.txt`) cubriendo vocabulario hospitalario + conversacional + números/nombres propios.
3. Para cada combinación modelo × locutor × longitud (3 s / 10 s / 30 s) × frase, generar el audio y persistir métricas:
   - WER: `faster-whisper large-v3 (ES)`
   - UTMOS: `tarepan/SpeechMOS utmos22_strong`
   - Sim WavLM: `microsoft/wavlm-large` cosine
   - Sim ECAPA: `speechbrain/spkrec-ecapa-voxceleb` cosine
   - AASIST: `clovaai/aasist`
   - Watermark: `resemble-perth verify` (nativo) o `audioseal verify` (post-hoc)
4. Cuadrar tabla comparativa contra los *decision gates* (ver [[Experimentos]]).

Salida esperada: `results/benchmark_<fecha>.csv` con 528 filas.

---

## Escenario D · Auditar un job sintetizado

**Objetivo:** que un auditor pueda comprobar la trazabilidad completa de un audio sintético: quién lo pidió, con qué consentimiento, qué modelo, qué watermark, qué score AASIST, y verificar que la cadena de hashes del audit log no ha sido manipulada.

```bash
# Verificar la integridad de la cadena
curl -fsS http://localhost:8000/audit/verify

# Filtrar por acción
curl -fsS "http://localhost:8000/audit/logs?action_prefix=synthesis.&limit=50"

# Filtrar por usuario
curl -fsS "http://localhost:8000/audit/logs?user_email=clinico@example.local&limit=50"

# Estadísticas
curl -fsS http://localhost:8000/audit/stats
```

Para cualquier `synthesis.id`, los campos clave persistidos son:
- `model` (chatterbox | omnivoice | qwen3 | elevenlabs)
- `consent_version` (referencia al texto firmado)
- `watermark_scheme` (perth | audioseal | none)
- `watermark_verified` (bool)
- `aasist_score` (float)
- `external_processor` (string · solo elevenlabs)
- `deployment_safe` (bool · false para elevenlabs)

Toda creación, lectura, modificación y entrega queda registrada en `audit_logs` con `prev_hash` y `hash` (SHA-256). La cadena se verifica con `GET /audit/verify` recorriendo de la última fila hacia atrás.
