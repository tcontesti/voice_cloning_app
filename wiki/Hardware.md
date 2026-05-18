# Hardware

> [[Home]] · Hardware

## Hardware del piloto

Servidor de inferencia de los workers de TTS, AASIST y AudioSeal.

| Atributo | Valor |
|---|---|
| Equipo | NVIDIA DGX Spark |
| Chip | Grace Blackwell GB10 |
| Arquitectura CPU | ARM64 (aarch64) |
| CUDA | 13.0 |
| VRAM unificada | 130 GB (Grace-Blackwell shared memory) |
| Sistema operativo | Linux (Ubuntu LTS) |
| Red | Interna del hospital; Tailscale opcional para acceso seguro |

Compartido con otros tenants del hospital (MedGemma 27B, DermApixel, motor ICA). El planificador interno reparte VRAM con LRU eviction tras 10 min idle por modelo.

## Por qué este hardware

- Memoria unificada Grace-Blackwell: permite mantener varios checkpoints residentes sin DMA explícito.
- Arquitectura ARM64 (aarch64): mejora consumo / Watt frente a x86 equivalente.
- CUDA 13.0: nativo para `torch 2.11.0+cu130`, ya validado con la stack del proyecto.
- Coste razonable comparado con clusters multi-A100; suficiente para 3 modelos TTS + AASIST + AudioSeal + un LLM clínico residente.

## Requisitos mínimos para piloto

| Tipo | Mínimo |
|---|---|
| GPU | NVIDIA con CUDA 12.4+ y ≥ 6 GB VRAM |
| RAM sistema | 16 GB (32 GB recomendado) |
| Disco | 50 GB libres (modelos + checkpoints + audios sintéticos del piloto) |
| Red | TLS 1.3 disponible, MagicDNS / DNS interno hospitalario |
| OS | Linux x86_64 o ARM64 con drivers NVIDIA |

## Recursos por modelo

| Modelo | VRAM mínima | VRAM cómoda | CPU/RAM | Notas |
|---|---|---|---|---|
| Chatterbox | 3.6 GB | 5 GB | 4 vCPU / 8 GB | Real-time |
| OmniVoice | 4.0 GB | 6 GB | 4 vCPU / 8 GB | No real-time, RTF 1.27 |
| Qwen3-TTS | 3.6 GB | 6 GB | 4 vCPU / 12 GB | Venv aislado `transformers<5` |
| AASIST | 1 GB | 2 GB | 2 vCPU / 4 GB | Singleton compartido |
| AudioSeal | 0.5 GB | 1 GB | 1 vCPU / 2 GB | Embed + verify |

## LRU eviction

Cada worker process mantiene un único modelo cargado a la vez. Tras 10 min de inactividad, libera VRAM. Esto permite compartir la Spark con otros servicios sin reservar memoria de forma permanente.

Lógica en `backend/app/workers/registry.py`.

## Tunneling y red

Despliegue multi-host (PC + Spark) en piloto:

- Autossh forward tunnels para Postgres, Redis, RabbitMQ, MinIO desde la Spark hacia la máquina del backend.
- Watchdog vía Task Scheduler en Windows con healthcheck del puerto del túnel (no solo del proceso autossh).
- Tailscale opcional como capa de red (MagicDNS atraviesa NAT vía DERP), sin integración en el código.

Documentado en `docs/dev_multihost.md`.

## Producción

En producción, todos los servicios corren en Kubernetes hospitalario, sin túneles. Helm chart `infra/helm/vcapp` con ExternalSecrets / SealedSecrets para credenciales y Vault transit para KMS.
