from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/eye_w"
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 дней

    # Суперпользователь создаётся при первом запуске, если такого логина ещё нет.
    # По умолчанию отключено: задайте значения в .env при необходимости bootstrap.
    superuser_login: str = ""
    superuser_password: str = ""
    superuser_name: str = ""

    # CORS: через переменную CORS_ORIGINS (через запятую).
    # Wildcard разрешается только если ALLOW_WILDCARD_CORS=true.
    cors_origins: str = ""
    allow_wildcard_cors: bool = False

    # Базовая защита от brute-force для /auth/login.
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
