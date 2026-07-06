from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres (direct connection, used by the fetch job for upserts)
    db_host: str
    db_port: int = 5432
    db_user: str
    db_password: str
    db_name: str = "postgres"

    # Unicommerce
    unicommerce_base_url: str = "https://jainam.unicommerce.com"
    unicommerce_client_id: str = "my-trusted-client"
    unicommerce_username: str
    unicommerce_password: str
    unicommerce_facilities: str  # comma-separated facility codes

    # Scheduler
    fetch_interval_minutes: int = 30

    # API
    cors_origins: str = "http://localhost:5173"

    @property
    def facilities(self) -> list[str]:
        return [f.strip() for f in self.unicommerce_facilities.split(",") if f.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
