from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: str
    owner_ids_raw: str = Field(default="", validation_alias="OWNER_IDS")
    database_url: str
    timezone: str = "Asia/Tehran"

    daily_report_hour: int = 23
    daily_report_minute: int = 0

    log_level: str = "INFO"
    log_file: str = "logs/bot.log"

    @cached_property
    def owner_ids(self) -> list[int]:
        return [
            int(part)
            for part in self.owner_ids_raw.replace(" ", "").split(",")
            if part
        ]


settings = Settings()


def setup_logging() -> None:
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    console = logging.StreamHandler()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[handler, console],
    )
    # aiogram and apscheduler are chatty at INFO
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
