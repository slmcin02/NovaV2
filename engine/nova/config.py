from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import os
import yaml
from dotenv import load_dotenv


@dataclass(slots=True)
class AppConfig:
    raw: dict[str, Any]

    @property
    def runtime(self) -> dict[str, Any]:
        return self.raw["runtime"]

    @property
    def universe(self) -> dict[str, Any]:
        return self.raw["universe"]

    @property
    def contracts(self) -> dict[str, Any]:
        return self.raw["contracts"]

    @property
    def scoring(self) -> dict[str, Any]:
        return self.raw["scoring"]

    @property
    def risk(self) -> dict[str, Any]:
        return self.raw["risk"]

    @property
    def storage(self) -> dict[str, Any]:
        return self.raw["storage"]

    @property
    def alerts(self) -> dict[str, Any]:
        return self.raw["alerts"]

    @property
    def edges(self) -> dict[str, Any]:
        return self.raw["edges"]

    @property
    def learner(self) -> dict[str, Any]:
        return self.raw.get("learner", {})

    @property
    def paper(self) -> dict[str, Any]:
        return self.raw.get("paper", {})

    @property
    def replay(self) -> dict[str, Any]:
        return self.raw.get("replay", {})

    @property
    def memory(self) -> dict[str, Any]:
        return self.raw.get("memory", {})

    @property
    def providers(self) -> dict[str, Any]:
        return self.raw.get("providers", {})

    @property
    def calibration(self) -> dict[str, Any]:
        return self.raw.get("calibration", {})


def load_config(path: str | Path = "config/app.yaml") -> AppConfig:
    load_dotenv()
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    data["env"] = {
        "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", "").strip(),
        "sec_user_agent": os.getenv("SEC_USER_AGENT", "Stephen personal research stephen@example.com").strip(),
        "thetadata_base_url": os.getenv("THETADATA_BASE_URL", "http://127.0.0.1:25503/v3").strip(),
        "polygon_api_key": os.getenv("POLYGON_API_KEY", "").strip(),
        "polygon_base_url": os.getenv("POLYGON_BASE_URL", "https://api.polygon.io").strip(),
        "fred_api_key": os.getenv("FRED_API_KEY", "").strip(),
        "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip(),
    }
    return AppConfig(raw=data)
