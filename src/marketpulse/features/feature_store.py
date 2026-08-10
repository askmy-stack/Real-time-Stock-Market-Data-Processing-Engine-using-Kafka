"""In-memory + DB feature store."""

from __future__ import annotations

from datetime import datetime

from marketpulse.config import get_settings
from marketpulse.db.repository import Repository
from marketpulse.features.rolling_features import RollingWindow
from marketpulse.schemas.events import StockFeatureEvent, StockTickEvent


class FeatureStore:
    def __init__(self, repo: Repository | None = None):
        self._windows: dict[str, RollingWindow] = {}
        self._repo = repo
        self._settings = get_settings()

    def _get_window(self, symbol: str) -> RollingWindow:
        symbol = symbol.upper()
        if symbol not in self._windows:
            self._windows[symbol] = RollingWindow(window_size=self._settings.rolling_window_size)
        return self._windows[symbol]

    def warm_start(self, repo: Repository | None = None) -> int:
        """Replay recent DB ticks into in-memory windows after a process restart.

        Loads up to ``rolling_window_size`` ticks per symbol (oldest → newest) so
        rolling stats are meaningful on the first live tick. Does not re-persist
        features. Returns the number of ticks loaded.
        """
        source = repo if repo is not None else self._repo
        if source is None:
            return 0

        limit = self._settings.rolling_window_size
        loaded = 0
        for symbol in source.get_symbols():
            # Repository returns newest-first; replay chronologically.
            rows = list(reversed(source.get_recent_ticks(symbol, limit=limit)))
            if not rows:
                continue
            window = self._get_window(symbol)
            for row in rows:
                window.add(float(row.price), int(row.volume))
                loaded += 1
        return loaded

    def process_tick(
        self, tick: StockTickEvent, repo: Repository | None = None
    ) -> StockFeatureEvent:
        window = self._get_window(tick.symbol)
        features = window.compute_all(tick.price, tick.volume)
        event = StockFeatureEvent(
            symbol=tick.symbol.upper(),
            timestamp=tick.timestamp or datetime.utcnow(),
            return_1m=features["return_1m"],
            return_5m=features["return_5m"],
            volatility=features["volatility"],
            z_score=features["z_score"],
            volume_ratio=features["volume_ratio"],
            price=features["price"],
            window_size=self._settings.rolling_window_size,
        )
        target = repo if repo is not None else self._repo
        if target:
            target.save_feature(event)
        return event

    def get_latest(self, symbol: str) -> StockFeatureEvent | None:
        if self._repo:
            row = self._repo.get_latest_features(symbol)
            if row:
                return StockFeatureEvent(
                    event_id=row.event_id,
                    symbol=row.symbol,
                    timestamp=row.timestamp,
                    return_1m=row.return_1m,
                    return_5m=row.return_5m,
                    volatility=row.volatility,
                    z_score=row.z_score,
                    volume_ratio=row.volume_ratio,
                    price=row.price,
                    window_size=row.window_size,
                )
        window = self._windows.get(symbol.upper())
        if not window or not window.ready:
            return None
        features = window.compute_all(window.prices[-1], window.volumes[-1])
        return StockFeatureEvent(
            symbol=symbol.upper(), **features, window_size=self._settings.rolling_window_size
        )
