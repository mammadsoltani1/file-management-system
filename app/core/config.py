from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str
    ENVIRONMENT: str
    DATABASE_URL: str
    SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    STORAGE_PROVIDER: str
    LOCAL_STORAGE_PATH: str
    MAX_UPLOAD_SIZE_BYTES: int

    REFRESH_TOKEN_EXPIRE_DAYS: int
    REFRESH_TOKEN_COOKIE_NAME: str
    REFRESH_TOKEN_COOKIE_SECURE: bool
    REFRESH_TOKEN_COOKIE_SAMESITE: str
    REFRESH_TOKEN_COOKIE_PATH: str

    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int
    EMAIL_VERIFICATION_FRONTEND_URL: str
    RESEND_API_URL: str
    RESEND_API_KEY: str
    EMAIL_FROM_ADDRESS: str
    EMAIL_FROM_NAME: str
    EMAIL_TIMEOUT_SECONDS: int


settings = Settings()
