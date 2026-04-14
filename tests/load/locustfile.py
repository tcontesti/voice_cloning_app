"""Locust scenarios — realistic clinical load for vcapp.

Usage:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8000

Scenarios (weights reflect expected clinical mix):
- Paciente: login, list own recordings, generate synthesis, poll status
- Clinico:  login, list all patients in own panel (future M9)
- Auditor:  login, browse audit log with filters

Each user authenticates once via POST /auth/login (mock OIDC).
"""

from __future__ import annotations

import random
import uuid

from locust import HttpUser, between, tag, task


def _maybe_get(response):
    """Robust JSON getter that tolerates non-JSON error bodies."""
    try:
        return response.json()
    except Exception:
        return {}


class PacienteUser(HttpUser):
    wait_time = between(2, 6)
    weight = 8

    def on_start(self) -> None:
        # In prod the seed creates paciente@hsll.es / paciente. For load
        # tests we use those creds directly (single shared account is OK for
        # read paths; for synthesis we want fresh per-VU state which the
        # user_id in the token handles).
        r = self.client.post(
            "/auth/login",
            json={"email": "paciente@hsll.es", "password": "paciente"},
            name="/auth/login",
        )
        if r.status_code != 200:
            self.environment.runner.quit()
            return
        self.token = r.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(5)
    @tag("read")
    def list_recordings(self) -> None:
        self.client.get("/recordings", headers=self.headers, name="/recordings")

    @task(3)
    @tag("read")
    def list_syntheses(self) -> None:
        self.client.get("/synthesis", headers=self.headers, name="/synthesis")

    @task(1)
    @tag("read")
    def models_meta(self) -> None:
        self.client.get("/synthesis/models", headers=self.headers, name="/synthesis/models")

    @task(1)
    @tag("write")
    def create_synthesis(self) -> None:
        # List profiles; if none, skip (profile creation requires an upload
        # which isn't part of this scenario — tested separately).
        profiles = _maybe_get(
            self.client.get("/profiles", headers=self.headers, name="/profiles")
        ).get("items") or []
        if not profiles:
            return
        text = random.choice([
            "Hola, buenos días.",
            "El paciente requiere descanso adicional.",
            "Por favor, tome la medicación después de las comidas.",
        ])
        self.client.post(
            "/synthesis",
            headers=self.headers,
            json={
                "profile_id": profiles[0]["id"],
                "model": random.choice(["chatterbox", "omnivoice"]),
                "text": text,
            },
            name="/synthesis [create]",
        )


class AuditorUser(HttpUser):
    wait_time = between(5, 15)
    weight = 1

    def on_start(self) -> None:
        r = self.client.post(
            "/auth/login",
            json={"email": "auditor@hsll.es", "password": "auditor"},
            name="/auth/login",
        )
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    @task(5)
    def browse_logs(self) -> None:
        self.client.get("/audit/logs?limit=50", headers=self.headers, name="/audit/logs")

    @task(2)
    def filter_by_action_prefix(self) -> None:
        prefix = random.choice(["auth.", "synthesis.", "recording.", "consent."])
        self.client.get(
            f"/audit/logs?action_prefix={prefix}&limit=50",
            headers=self.headers, name="/audit/logs [prefix]",
        )

    @task(1)
    def verify_chain(self) -> None:
        self.client.get("/audit/verify", headers=self.headers, name="/audit/verify")

    @task(1)
    def stats(self) -> None:
        self.client.get("/audit/stats", headers=self.headers, name="/audit/stats")


class HealthCheckUser(HttpUser):
    """Simulates k8s liveness/readiness traffic."""
    wait_time = between(1, 3)
    weight = 1

    @task
    def health(self) -> None:
        self.client.get("/health", name="/health")

    @task
    def metrics(self) -> None:
        self.client.get("/metrics", name="/metrics")


# Bogus unused import to keep ruff quiet if we later add UUID-based VUs
_ = uuid
