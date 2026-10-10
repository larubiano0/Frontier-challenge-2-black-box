"""Configuration from environment variables. No credentials are hardcoded."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    token: str | None
    host: str = "0.0.0.0"
    port: int = 8000


def get_settings() -> Settings:
    """Read settings at call time so tests can change the environment."""
    return Settings(
        token=os.environ.get("FRONTIER_TOKEN") or None,
        port=int(os.environ.get("PORT", "8000")),
    )
