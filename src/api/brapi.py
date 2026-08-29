from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests
from requests.exceptions import JSONDecodeError, RequestException, Timeout

from src.models.stock import ChartPeriod, HistoricalPoint, StockHistory, StockQuote

logger = logging.getLogger(__name__)

BASE_URL = "https://brapi.dev/api/v2/stocks"
DEFAULT_TIMEOUT = 15


class BrapiError(Exception):
    """Erro retornado ou derivado da API brapi.dev."""


class BrapiClient:
    def __init__(self, token: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._token = token
        self._timeout = timeout
        self._session = requests.Session()

    def set_token(self, token: str | None) -> None:
        self._token = token.strip() if token else None

    def _headers(self) -> dict[str, str]:
        if not self._token:
            return {}
        return {"Authorization": f"Bearer {self._token}"}

    def _request(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{BASE_URL}/{path}"
        try:
            response = self._session.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self._timeout,
            )
        except Timeout as exc:
            raise BrapiError("Tempo esgotado ao contactar a brapi.dev") from exc
        except RequestException as exc:
            raise BrapiError("Sem conexão com a brapi.dev") from exc

        if response.status_code == 429:
            raise BrapiError("Limite de requisições da brapi.dev excedido")
        if response.status_code in (401, 403):
            raise BrapiError("Token da brapi.dev inválido ou ausente")
        if response.status_code >= 400:
            raise BrapiError(f"Erro da API brapi.dev ({response.status_code})")

        try:
            payload: dict[str, Any] = response.json()
        except JSONDecodeError as exc:
            raise BrapiError("Resposta inválida da brapi.dev") from exc

        return payload

    @staticmethod
    def _parse_quote_item(item: dict[str, Any], fallback_symbol: str = "") -> StockQuote:
        symbol = (
            item.get("requestedSymbol")
            or item.get("symbol")
            or fallback_symbol
        ).upper()

        nested = item.get("data")
        if isinstance(nested, dict) and nested:
            data: dict[str, Any] = nested
        else:
            data = item

        updated_at: datetime | None = None
        raw_time = data.get("regularMarketTime")
        if raw_time:
            try:
                updated_at = datetime.fromisoformat(str(raw_time).replace("Z", "+00:00"))
            except ValueError:
                updated_at = None

        return StockQuote(
            symbol=symbol,
            price=data.get("regularMarketPrice"),
            change=data.get("regularMarketChange"),
            change_percent=data.get("regularMarketChangePercent"),
            currency=data.get("currency") or "BRL",
            short_name=data.get("shortName"),
            long_name=data.get("longName"),
            updated_at=updated_at,
            market_open=data.get("regularMarketOpen"),
            day_high=data.get("regularMarketDayHigh"),
            day_low=data.get("regularMarketDayLow"),
        )

    @staticmethod
    def _parse_history_points(raw_points: list[dict[str, Any]]) -> tuple[HistoricalPoint, ...]:
        points: list[HistoricalPoint] = []
        for item in raw_points:
            timestamp = item.get("date")
            close = item.get("adjustedClose") or item.get("close")
            if timestamp is None or close is None:
                continue
            points.append(
                HistoricalPoint(
                    date=datetime.fromtimestamp(int(timestamp), tz=timezone.utc),
                    close=float(close),
                )
            )
        points.sort(key=lambda point: point.date)
        return tuple(points)

    def _fetch_quote_payload(self, symbol: str) -> dict[str, Any]:
        return self._request("quote", params={"symbols": symbol.upper()})

    def fetch_quote(self, symbol: str) -> StockQuote:
        symbol = symbol.upper()
        try:
            payload = self._fetch_quote_payload(symbol)
        except BrapiError:
            raise

        results = payload.get("results") or []
        if not results:
            return StockQuote(
                symbol=symbol,
                price=None,
                change=None,
                change_percent=None,
                currency="BRL",
                short_name=None,
                long_name=None,
                updated_at=None,
                error="Sem dados",
            )

        quote = self._parse_quote_item(results[0], fallback_symbol=symbol)
        if quote.price is None and quote.error is None:
            quote = StockQuote(
                symbol=symbol,
                price=None,
                change=None,
                change_percent=None,
                currency="BRL",
                short_name=quote.short_name,
                long_name=quote.long_name,
                updated_at=quote.updated_at,
                error="Cotação indisponível",
            )
        return quote

    def fetch_quotes(self, symbols: list[str]) -> list[StockQuote]:
        """Busca cotações uma a uma (plano gratuito: 1 ativo por requisição)."""
        if not symbols:
            return []

        quotes: list[StockQuote] = []
        for symbol in symbols:
            try:
                quotes.append(self.fetch_quote(symbol))
            except BrapiError as exc:
                logger.warning("Erro ao buscar cotação de %s: %s", symbol, exc)
                quotes.append(
                    StockQuote(
                        symbol=symbol.upper(),
                        price=None,
                        change=None,
                        change_percent=None,
                        currency="BRL",
                        short_name=None,
                        long_name=None,
                        updated_at=None,
                        error=str(exc),
                    )
                )
        return quotes

    def fetch_history(self, symbol: str, period: ChartPeriod, *, interval: str) -> StockHistory:
        symbol = symbol.upper()
        payload = self._request(
            "historical",
            params={
                "symbols": symbol,
                "range": period.range,
                "interval": interval,
            },
        )
        results = payload.get("results") or []
        if not results:
            return StockHistory(
                symbol=symbol,
                period=period,
                points=(),
                error="Sem dados históricos",
            )

        item = results[0]
        data = item.get("data") or {}
        raw_points = data.get("historicalDataPrice") or []
        points = self._parse_history_points(raw_points)

        if not points:
            return StockHistory(
                symbol=symbol,
                period=period,
                points=(),
                error="Sem dados históricos",
            )

        return StockHistory(symbol=symbol, period=period, points=points)
