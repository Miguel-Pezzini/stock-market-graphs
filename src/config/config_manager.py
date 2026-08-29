from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.models.stock import FREE_PLAN_PERIODS, ChartPeriod

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".config" / "stock-desktop"
CONFIG_FILE = CONFIG_DIR / "config.json"
TOKEN_FILE = CONFIG_DIR / "token"

DEFAULT_STOCKS = ["KLBN4", "TAEE11", "BBAS3", "RINV11", "BBDC3", "CSMG3"]
VALID_THEMES = frozenset({"system", "light", "dark"})
VALID_WINDOW_MODES = frozenset({"normal", "desktop_widget"})
VALID_PERIODS = frozenset({"1d", "5d", "1mo", "6mo", "1y"})
VALID_API_PLANS = frozenset({"free", "paid"})


@dataclass
class AppConfig:
    stocks: list[str] = field(default_factory=lambda: DEFAULT_STOCKS.copy())
    refresh_interval: int = 300
    default_period: str = "1d"
    columns: int = 3
    theme: str = "system"
    window_mode: str = "normal"
    api_plan: str = "free"
    card_width: int = 280
    card_height: int = 205
    window_width: int = 520
    window_height: int = 280
    window_x: int | None = None
    window_y: int | None = None
    card_periods: dict[str, str] = field(default_factory=dict)
    card_positions: dict[str, dict[str, int]] = field(default_factory=dict)


class ConfigManager:
    def __init__(self, config_path: Path = CONFIG_FILE) -> None:
        self._config_path = config_path

    def load(self) -> AppConfig:
        if not self._config_path.exists():
            logger.info("Config não encontrada em %s; usando defaults", self._config_path)
            config = AppConfig()
            self.save(config)
            return config

        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Falha ao ler config (%s); usando defaults", exc)
            return AppConfig()

        return self._parse_raw(raw)

    def save(self, config: AppConfig) -> None:
        normalized = self.normalize(config)
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "stocks": normalized.stocks,
            "refresh_interval": normalized.refresh_interval,
            "default_period": normalized.default_period,
            "columns": normalized.columns,
            "theme": normalized.theme,
            "window_mode": normalized.window_mode,
            "api_plan": normalized.api_plan,
            "card_width": normalized.card_width,
            "card_height": normalized.card_height,
            "window_width": normalized.window_width,
            "window_height": normalized.window_height,
            "window_x": normalized.window_x,
            "window_y": normalized.window_y,
            "card_periods": normalized.card_periods,
            "card_positions": normalized.card_positions,
        }
        self._config_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _parse_raw(self, raw: dict[str, Any]) -> AppConfig:
        stocks = [str(symbol).upper() for symbol in raw.get("stocks", DEFAULT_STOCKS)]
        card_periods = {
            str(symbol).upper(): str(period)
            for symbol, period in dict(raw.get("card_periods", {})).items()
        }

        return self.normalize(
            AppConfig(
                stocks=stocks,
                refresh_interval=int(raw.get("refresh_interval", 300)),
                default_period=str(raw.get("default_period", "1d")),
                columns=int(raw.get("columns", 3)),
                theme=str(raw.get("theme", "system")),
                window_mode=str(raw.get("window_mode", "normal")),
                api_plan=str(raw.get("api_plan", "free")),
                card_width=int(raw.get("card_width", 268)),
                card_height=int(raw.get("card_height", 190)),
                window_width=int(raw.get("window_width", 520)),
                window_height=int(raw.get("window_height", 280)),
                window_x=self._optional_int(raw.get("window_x")),
                window_y=self._optional_int(raw.get("window_y")),
                card_periods=card_periods,
                card_positions=dict(raw.get("card_positions", {})),
            )
        )

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def normalize(config: AppConfig) -> AppConfig:
        config.stocks = [symbol.upper() for symbol in config.stocks if symbol.strip()]
        if not config.stocks:
            config.stocks = DEFAULT_STOCKS.copy()

        config.refresh_interval = max(60, min(config.refresh_interval, 86_400))
        config.columns = max(1, min(config.columns, 6))
        config.card_width = max(260, min(config.card_width, 320))
        config.card_height = max(195, min(config.card_height, 240))
        config.window_width = max(560, min(config.window_width, 1600))
        config.window_height = max(320, min(config.window_height, 1200))

        if config.default_period not in VALID_PERIODS:
            config.default_period = "1d"
        if config.theme not in VALID_THEMES:
            config.theme = "system"
        if config.window_mode not in VALID_WINDOW_MODES:
            config.window_mode = "normal"
        if config.api_plan not in VALID_API_PLANS:
            config.api_plan = "free"

        allowed_ranges = (
            {period.range for period in ChartPeriod}
            if config.api_plan == "paid"
            else {period.range for period in FREE_PLAN_PERIODS}
        )
        if config.default_period not in allowed_ranges:
            config.default_period = "1d"

        config.card_periods = {
            symbol.upper(): period
            for symbol, period in config.card_periods.items()
            if period in allowed_ranges
        }

        return config

    def set_card_period(self, config: AppConfig, symbol: str, period_range: str) -> None:
        if period_range not in VALID_PERIODS:
            return
        config.card_periods[symbol.upper()] = period_range
        self.save(config)

    def set_card_position(self, config: AppConfig, symbol: str, x: int, y: int) -> None:
        config.card_positions[symbol.upper()] = {"x": int(x), "y": int(y)}
        self.save(config)

    def update_window_state(
        self,
        config: AppConfig,
        *,
        width: int,
        height: int,
        x: int | None = None,
        y: int | None = None,
    ) -> None:
        config.window_width = width
        config.window_height = height
        if x is not None:
            config.window_x = x
        if y is not None:
            config.window_y = y
        self.save(config)

    @staticmethod
    def load_token() -> str | None:
        env_token = os.environ.get("BRAPI_TOKEN")
        if env_token:
            return env_token.strip() or None

        if TOKEN_FILE.exists():
            token = TOKEN_FILE.read_text(encoding="utf-8").strip()
            return token or None

        return None

    @staticmethod
    def save_token(token: str) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token.strip() + "\n", encoding="utf-8")

    @staticmethod
    def has_saved_token() -> bool:
        return TOKEN_FILE.exists() and bool(ConfigManager.load_token())
