from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, RedisDsn, HttpUrl, SecretStr


class Settings(BaseSettings):
    APP_NAME: str = "PingMe"
    DEBUG: bool = False

    # Logging settings
    LOG_FORMAT: str = "json"  # "json" or "text"
    LOG_FILE: str | None = "logs/app.log"  # Path to log file, None for stdout only
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    
    @property
    def REDIS_URL(self) -> RedisDsn:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    WS_MESSAGE_QUEUE_SIZE: int = 1000
    WS_HEARTBEAT_INTERVAL: int = 30
    
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: SecretStr
    GOOGLE_REDIRECT_URI: HttpUrl
    
    PASSWORD_MIN_LENGTH: int = 6
    PASSWORD_MAX_LENGTH: int = 72
    
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: SecretStr
    SMTP_FROM_EMAIL: str

    # Cache settings
    CACHE_TTL: int = 1800  # 30 minutes default TTL

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
