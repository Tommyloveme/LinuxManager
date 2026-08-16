from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CEDAR_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "Cedar"
    app_version: str = "1.0.0"
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    secret_key: str = "change-this-secret-in-production"
    access_token_expire_minutes: int = 12 * 60
    admin_username: str = "admin"
    admin_password: str = "changeme"
    data_dir: Path = Path("./data")
    allow_user_switch: bool = True
    command_timeout: int = 120
    max_output_bytes: int = 2 * 1024 * 1024
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    @property
    def database_url(self) -> str:
        db_path = (self.data_dir / "cedar.db").resolve()
        return f"sqlite+aiosqlite:///{db_path.as_posix()}"

    @property
    def archive_dir(self) -> Path:
        return self.data_dir / "archives"

    @property
    def job_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def script_dir(self) -> Path:
        return self.data_dir / "scripts"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.archive_dir, self.job_dir, self.script_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
