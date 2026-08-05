import pytest

from strategy.base import BaseStrategy
from strategy.registry import STRATEGY_REGISTRY, get_strategy, load_strategies, register_strategy


def test_registry_loading():
    # make sure registry is empty or clear it for testing if needed.
    load_strategies()
    assert "sma" in STRATEGY_REGISTRY
    assert "ema" in STRATEGY_REGISTRY
    assert "rsi" in STRATEGY_REGISTRY
    assert "macd" in STRATEGY_REGISTRY


def test_get_strategy():
    load_strategies()
    strategy_cls = get_strategy("sma")
    assert issubclass(strategy_cls, BaseStrategy)


def test_get_invalid_strategy():
    with pytest.raises(ValueError):
        get_strategy("non_existent_strategy_999")


def test_decorator_invalid_class():
    with pytest.raises(TypeError):

        @register_strategy("bad")
        class BadStrategy:
            pass
