# Load tests

Realistic clinical load mix using [Locust](https://locust.io).

```bash
pip install locust
locust -f tests/load/locustfile.py --host http://localhost:8000
# open http://localhost:8089
```

## Scenarios

| User class        | Weight | Behaviour                                       |
|-------------------|-------:|-------------------------------------------------|
| PacienteUser      |      8 | login → list recordings/syntheses → create synth |
| AuditorUser       |      1 | login → browse/filter audit log                 |
| HealthCheckUser   |      1 | /health + /metrics (simulates k8s probes)       |

## Target numbers for MVP (5–20 patients/day)

- Median API latency < 200 ms (excluding synthesis enqueue which hits RabbitMQ)
- p95 API latency < 500 ms
- Synthesis enqueue (POST /synthesis) < 300 ms (no model load here — worker side)
- No 5xx under 50 concurrent VUs

## Not measured here

- TTS generation time (RTF): that's a worker-side benchmark, see the original
  `voice_cloning/scripts/run_benchmark.py`.
- WebSocket progress stream latency: covered by a follow-up M8+ scenario.
