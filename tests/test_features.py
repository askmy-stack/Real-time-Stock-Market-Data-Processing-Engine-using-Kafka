"""Test rolling feature calculations."""

from marketpulse.features.rolling_features import RollingWindow


def test_rolling_window_returns():
    window = RollingWindow(window_size=10)
    prices = [100, 101, 102, 103, 104]
    for i, p in enumerate(prices):
        features = window.compute_all(p, 1000 + i * 100)
    assert features["return_1m"] > 0
    assert features["price"] == 104


def test_rolling_window_z_score():
    window = RollingWindow(window_size=20)
    for p in [100.0] * 19:
        window.compute_all(p, 1000)
    features = window.compute_all(110.0, 5000)
    assert abs(features["z_score"]) > 1


def test_volume_ratio_spike():
    window = RollingWindow(window_size=10)
    for _ in range(5):
        window.compute_all(100.0, 1000)
    features = window.compute_all(100.0, 10000)
    assert features["volume_ratio"] > 1.5


class _TickRow:
    def __init__(self, price: float, volume: int):
        self.price = price
        self.volume = volume


class _FakeRepo:
    def __init__(self, ticks_by_symbol: dict[str, list[_TickRow]]):
        self._ticks = ticks_by_symbol

    def get_symbols(self) -> list[str]:
        return sorted(self._ticks)

    def get_recent_ticks(self, symbol: str, limit: int = 50, offset: int = 0):
        # Newest-first, matching Repository.get_recent_ticks
        rows = list(reversed(self._ticks[symbol.upper()]))
        return rows[offset : offset + limit]


def test_feature_store_warm_start_replays_ticks_chronologically():
    from marketpulse.features.feature_store import FeatureStore

    repo = _FakeRepo(
        {
            "AAPL": [_TickRow(100.0 + i, 1000 + i) for i in range(5)],
        }
    )
    store = FeatureStore()
    loaded = store.warm_start(repo)
    assert loaded == 5
    window = store._windows["AAPL"]
    assert list(window.prices) == [100.0, 101.0, 102.0, 103.0, 104.0]
    assert window.ready is True


def test_feature_store_warm_start_noop_without_repo():
    from marketpulse.features.feature_store import FeatureStore

    assert FeatureStore().warm_start() == 0


def test_feature_store_warm_start_caps_at_window_size(monkeypatch):
    from marketpulse.config import get_settings
    from marketpulse.features.feature_store import FeatureStore

    settings = get_settings()
    monkeypatch.setattr(settings, "rolling_window_size", 3)
    repo = _FakeRepo({"MSFT": [_TickRow(float(i), i) for i in range(10)]})
    store = FeatureStore()
    assert store.warm_start(repo) == 3
    assert list(store._windows["MSFT"].prices) == [7.0, 8.0, 9.0]
