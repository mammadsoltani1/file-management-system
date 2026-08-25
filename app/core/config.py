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


settings = Settings()
