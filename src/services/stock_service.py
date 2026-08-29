from __future__ import annotations

import logging
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from src.api.brapi import BrapiClient, BrapiError
from src.models.stock import ChartPeriod, StockHistory, StockQuote

logger = logging.getLogger(__name__)

HISTORY_CACHE_TTL_SECONDS = 3600


@dataclass
class _HistoryCacheEntry:
    history: StockHistory
    expires_at: float


class StockService:
    def __init__(self, client: BrapiClient, max_workers: int = 4) -> None:
        self._client = client
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="stock-fetch",
        )
        self._history_cache: dict[tuple[str, str], _HistoryCacheEntry] = {}

    @property
    def client(self) -> BrapiClient:
        return self._client

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def fetch_quotes_async(
        self,
        symbols: list[str],
        on_success: Callable[[list[StockQuote]], bool | None],
        on_error: Callable[[str], bool | None] | None = None,
    ) -> Future[list[StockQuote]]:
        return self._run_async(
            task=lambda: self._fetch_quotes_safe(symbols),
            on_success=on_success,
            on_error=on_error,
            label=f"cotações ({len(symbols)} ativos)",
        )

    def fetch_quote_async(
        self,
        symbol: str,
        on_success: Callable[[StockQuote], bool | None],
        on_error: Callable[[str], bool | None] | None = None,
    ) -> Future[StockQuote]:
        return self._run_async(
            task=lambda: self._fetch_quote_safe(symbol),
            on_success=on_success,
            on_error=on_error,
            label=f"cotação de {symbol}",
        )

    def fetch_history_async(
        self,
        symbol: str,
        period: ChartPeriod,
        on_success: Callable[[StockHistory], bool | None],
        on_error: Callable[[str], bool | None] | None = None,
        *,
        interval: str,
        force_refresh: bool = False,
    ) -> Future[StockHistory] | None:
        cache_key = (symbol, period.range, interval)
        if not force_refresh:
            cached = self._history_cache.get(cache_key)
            if cached and cached.expires_at > time.monotonic():
                GLib.idle_add(on_success, cached.history)
                return None

        return self._run_async(
            task=lambda: self._fetch_history_safe(symbol, period, interval),
            on_success=self._wrap_history_success(cache_key, on_success),
            on_error=on_error,
            label=f"histórico de {symbol} ({period.label})",
        )

    def _wrap_history_success(
        self,
        cache_key: tuple[str, str],
        on_success: Callable[[StockHistory], bool | None],
    ) -> Callable[[StockHistory], bool | None]:
        def _handler(history: StockHistory) -> bool | None:
            if history.has_data:
                self._history_cache[cache_key] = _HistoryCacheEntry(
                    history=history,
                    expires_at=time.monotonic() + HISTORY_CACHE_TTL_SECONDS,
                )
            return on_success(history)

        return _handler

    def _run_async(
        self,
        task: Callable[[], object],
        on_success: Callable[[object], bool | None],
        on_error: Callable[[str], bool | None] | None,
        label: str,
    ) -> Future[object]:
        future = self._executor.submit(task)

        def _done(fut: Future[object]) -> None:
            try:
                result = fut.result()
            except Exception as exc:  # noqa: BLE001 — callback de UI
                logger.exception("Falha inesperada ao buscar %s", label)
                if on_error:
                    GLib.idle_add(on_error, str(exc))
                return

            GLib.idle_add(on_success, result)

        future.add_done_callback(_done)
        return future

    def _fetch_quotes_safe(self, symbols: list[str]) -> list[StockQuote]:
        return self._client.fetch_quotes(symbols)

    def _fetch_quote_safe(self, symbol: str) -> StockQuote:
        try:
            return self._client.fetch_quote(symbol)
        except BrapiError as exc:
            logger.warning("Erro ao buscar cotação de %s: %s", symbol, exc)
            return StockQuote(
                symbol=symbol,
                price=None,
                change=None,
                change_percent=None,
                currency="BRL",
                short_name=None,
                long_name=None,
                updated_at=None,
                error=str(exc),
            )

    def _fetch_history_safe(
        self,
        symbol: str,
        period: ChartPeriod,
        interval: str,
    ) -> StockHistory:
        try:
            return self._client.fetch_history(symbol, period, interval=interval)
        except BrapiError as exc:
            logger.warning(
                "Erro ao buscar histórico de %s (%s): %s",
                symbol,
                period.label,
                exc,
            )
            return StockHistory(
                symbol=symbol,
                period=period,
                points=(),
                error=str(exc),
            )
