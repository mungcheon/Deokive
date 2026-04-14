from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Deokive API"
    app_env: str = "development"
    database_url: str = "sqlite:///./deokive_dev.db"
    jwt_secret_key: str = "change-this-secret-key"
    admin_jwt_secret_key: str = "change-this-admin-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    admin_jwt_expire_minutes: int = 60 * 12
    bootstrap_admin_email: str = "admin"
    bootstrap_admin_password: str = "admin"
    bootstrap_admin_name: str = "Deokive Admin"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
