from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Shioaji
    SHIOAJI_API_KEY: Optional[str] = None
    SHIOAJI_SECRET_KEY: Optional[str] = None

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ALLOWLIST: str = ""

    # Security
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Database
    DATABASE_URL: str = "sqlite:///./stockhelm.db"

    # Admin User
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    @property
    def telegram_allowlist_ids(self) -> List[int]:
        return [int(x.strip()) for x in self.TELEGRAM_ALLOWLIST.split(",") if x.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
