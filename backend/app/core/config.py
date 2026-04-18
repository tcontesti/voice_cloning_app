from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = Field(default="dev")
    app_log_level: str = Field(default="INFO")
    app_secret_key: str = Field(default="dev-only-do-not-use-in-prod")

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "vcapp"
    postgres_password: str = ""
    postgres_db: str = "vcapp"

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""

    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "vcapp"
    rabbitmq_password: str = ""

    minio_host: str = "minio"
    minio_port: int = 9000
    minio_root_user: str = "vcapp"
    minio_root_password: str = ""
    minio_bucket_recordings: str = "recordings"
    minio_bucket_syntheses: str = "syntheses"

    kms_mode: str = "mock"
    kms_mock_key: str = "ZGV2LWtleS0zMi1ieXRlcy1tdXN0LWJlLWxvbmctZW5vdWdoLW9rPT0="

    vault_addr: str = ""
    vault_token: str = ""
    vault_transit_key: str = "vcapp-master"

    auth_mode: str = "mock"  # mock | keycloak
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""

    # SSE-C requires HTTPS to MinIO. Enable in prod with TLS termination
    # in front of MinIO; "none" is for dev only.
    storage_encryption: str = "none"
    minio_secure: bool = False

    cors_allowed_origins: str = ""

    # ElevenLabs cloud adapter. Disabled by default — when enabled the
    # /synthesis/models endpoint exposes it and the worker_elevenlabs
    # queue is expected to be up. The rest of these are adapter knobs
    # consumed by app/workers/adapters/elevenlabs.py; missing them at
    # attribute access raised AttributeError at synthesis time and the
    # job crashed with "Settings' object has no attribute ..." in the
    # error column, which is how we found the gap.
    elevenlabs_enabled: bool = False
    elevenlabs_api_key: str = ""
    # Default tuned for the spoken clinical-text length (~500 chars);
    # bumps to 90 give ElevenLabs room for the synthesis call itself
    # on top of slow network.
    elevenlabs_http_timeout_s: float = 90.0
    elevenlabs_retry_max_attempts: int = 4
    # IVC accepts up to 25 files — but 8 refs covers clinical needs and
    # keeps the multipart body well under the 11 MB hard cap.
    elevenlabs_max_refs: int = 8
    # Re-cloning the same voice costs IVC quota; 24 h cache is what the
    # adapter assumes and what ops scoped for.
    elevenlabs_voice_cache_ttl_s: int = 24 * 60 * 60
    # Default model ID — overridable per-job via options.model_id.
    elevenlabs_model_id: str = "eleven_multilingual_v2"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
