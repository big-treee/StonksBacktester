import pytest

from strategy.base import BaseStrategy
from strategy.validation import ParameterValidationError, validate_strategy_parameters


class DummyStrategy(BaseStrategy):
    required_parameters = {"fast": int, "ratio": float}

    def initialize(self) -> None:
        pass

    def on_market_event(self, event) -> None:
        pass

    def generate_signals(self, event) -> None:
        pass

    def reset(self) -> None:
        pass


def test_validation_success():
    params = {"fast": 10, "ratio": 1.5}
    # should not raise.
    validate_strategy_parameters(DummyStrategy, params)


def test_validation_int_as_float():
    params = {"fast": 10, "ratio": 1}  # is int but float expected.
    # should not raise we allow int where float is expected.
    validate_strategy_parameters(DummyStrategy, params)


def test_validation_missing_param():
    params = {"fast": 10}
    with pytest.raises(ParameterValidationError) as excinfo:
        validate_strategy_parameters(DummyStrategy, params)
    assert "Missing required parameter" in str(excinfo.value)


def test_validation_wrong_type():
    params = {"fast": "10", "ratio": 1.5}
    with pytest.raises(ParameterValidationError) as excinfo:
        validate_strategy_parameters(DummyStrategy, params)
    assert "Invalid type" in str(excinfo.value)
