from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn, HttpUrl, SecretStr
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    # -------------- APP CONFIG --------------
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    APP_NAME: str = "PingMe"
    DEBUG: bool = False

    CORS_ORIGINS: list[str] = ["*"]

    # -------------- Logging CONFIG --------------
    SQLALCHEMY_ECHO: bool = False

    LOG_SENSITIVE_DATA: list[str] = []
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = (
        "%(asctime)s | %(levelname)-8s | %(name)s | "
        "[%(filename)s:%(funcName)s:%(lineno)d] - %(message)s"
    )
    LOG_DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    _LOGS_DIR: Path = BASE_DIR / "logs"

    @property
    def LOGS_DIR(self) -> Path:
        Path.mkdir(self._LOGS_DIR, parents=True, exist_ok=True)
        return self._LOGS_DIR

    # -------------- DB CONFIG --------------
    DB_USER: str
    DB_PASS: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # -------------- REDIS CONFIG --------------
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASS: str | None = None
    
    @property
    def REDIS_URL(self) -> RedisDsn:
        auth = f":{self.REDIS_PASS}@" if not self.DEBUG else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # -------------- JWT --------------
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE: int = 30 * 60 # In seconds
    JWT_REFRESH_TOKEN_EXPIRE: int = 30 * 24 * 60 * 60 # In seconds

    # -------------- GOOGLE --------------
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: SecretStr
    GOOGLE_REDIRECT_URI: HttpUrl

    # -------------- SMTP --------------
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: SecretStr
    SMTP_FROM_EMAIL: str


    # -------------- ADDITIONAL APP SETTINGS --------------
    PASSWORD_MIN_LENGTH: int = 6
    PASSWORD_MAX_LENGTH: int = 72

    WS_MESSAGE_QUEUE_SIZE: int = 1000
    WS_HEARTBEAT_INTERVAL: int = 30

    CACHE_TTL: int = 1800  # 30 minutes default TTL


settings = Settings()
