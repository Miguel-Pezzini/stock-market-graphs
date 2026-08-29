from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ChartPeriod(Enum):
    ONE_DAY = ("1D", "1d")
    FIVE_DAYS = ("5D", "5d")
    ONE_MONTH = ("1M", "1mo")
    SIX_MONTHS = ("6M", "6mo")
    ONE_YEAR = ("1Y", "1y")

    def __init__(self, label: str, range: str) -> None:
        self.label = label
        self.range = range

    @classmethod
    def from_api_range(cls, api_range: str) -> ChartPeriod | None:
        for period in cls:
            if period.range == api_range:
                return period
        return None


# Períodos disponíveis no plano gratuito da brapi (histórico até 3 meses).
FREE_PLAN_PERIODS = frozenset({ChartPeriod.ONE_DAY, ChartPeriod.FIVE_DAYS, ChartPeriod.ONE_MONTH})

FREE_PLAN_TOOLTIP = (
    "Indisponível no plano gratuito da brapi (histórico limitado a 3 meses). "
    'Altere "api_plan" para "paid" no config se tiver plano pago.'
)


def periods_for_plan(plan: str) -> frozenset[ChartPeriod]:
    if plan == "paid":
        return frozenset(ChartPeriod)
    return FREE_PLAN_PERIODS


def interval_for_plan(period: ChartPeriod, api_plan: str) -> str:
    """Intervalo histórico aceito pela brapi para o plano atual."""
    if period is ChartPeriod.ONE_DAY:
        return "5m" if api_plan == "paid" else "1d"
    return "1d"


@dataclass(frozen=True, slots=True)
class HistoricalPoint:
    date: datetime
    close: float


@dataclass(frozen=True, slots=True)
class StockHistory:
    symbol: str
    period: ChartPeriod
    points: tuple[HistoricalPoint, ...]
    error: str | None = None

    @property
    def closes(self) -> list[float]:
        return [point.close for point in self.points]

    @property
    def has_data(self) -> bool:
        return bool(self.points) and self.error is None


@dataclass(frozen=True, slots=True)
class StockQuote:
    symbol: str
    price: float | None
    change: float | None
    change_percent: float | None
    currency: str
    short_name: str | None
    long_name: str | None
    updated_at: datetime | None
    market_open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    error: str | None = None

    def synthesize_day_closes(self) -> list[float] | None:
        """Aproxima o pregão do dia com OHLC quando não há intraday."""
        if self.price is None or self.market_open is None:
            return None

        open_price = self.market_open
        close = self.price
        high = self.day_high if self.day_high is not None else max(open_price, close)
        low = self.day_low if self.day_low is not None else min(open_price, close)

        if close >= open_price:
            return [open_price, low, high, close]
        return [open_price, high, low, close]

    @property
    def is_positive(self) -> bool:
        if self.change_percent is None:
            return True
        return self.change_percent >= 0

    @property
    def has_data(self) -> bool:
        return self.price is not None and self.error is None
