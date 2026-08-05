from typing import Any, Type


class ParameterValidationError(ValueError):
    """exception raised for invalid strategy parameters."""

    pass


def validate_strategy_parameters(strategy_class: Type, parameters: dict[str, Any]) -> None:
    """validates provided parameters against required metadata."""
    required = getattr(strategy_class, "required_parameters", {})

    for param_name, expected_type in required.items():
        if param_name not in parameters:
            strat_name = strategy_class.__name__
            msg = f"Missing required parameter '{param_name}' for strategy '{strat_name}'."
            raise ParameterValidationError(msg)

        value = parameters[param_name]

        if expected_type is float and isinstance(value, int):
            continue

        if not isinstance(value, expected_type):
            strat_name = strategy_class.__name__
            exp_name = expected_type.__name__
            got_name = type(value).__name__
            msg = f"Invalid type for parameter '{param_name}' in '{strat_name}'. Expected {exp_name}, got {got_name}."
            raise ParameterValidationError(msg)
