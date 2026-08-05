import importlib
import os
import sys
from typing import Callable, Type

from strategy.base import BaseStrategy

# the global registry.
STRATEGY_REGISTRY: dict[str, Type[BaseStrategy]] = {}


def register_strategy(name: str) -> Callable:
    """decorator to register a strategy class into the registry."""

    def decorator(cls: Type[BaseStrategy]) -> Type[BaseStrategy]:
        if not issubclass(cls, BaseStrategy):
            raise TypeError(f"Registered class {cls.__name__} must inherit from BaseStrategy.")
        STRATEGY_REGISTRY[name] = cls
        cls.strategy_name = name
        return cls

    return decorator


def get_strategy(name: str) -> Type[BaseStrategy]:
    """retrieves a strategy class from the registry by its registered name."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Strategy '{name}' not found. Available: {list(STRATEGY_REGISTRY.keys())}"
        )
    return STRATEGY_REGISTRY[name]


def list_registered_strategies() -> list[str]:
    """returns a list of all registered strategy names."""
    return list(STRATEGY_REGISTRY.keys())


def load_strategies(plugins_dir: str = "strategies") -> None:
    """dynamically loads all python modules from the specified directory.
    so that the register strategy decorators are executed."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, plugins_dir)

    if not os.path.exists(target_dir):
        return

    # temporarily add base dir to path so importlib can find plugins.
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    for filename in os.listdir(target_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = f"{plugins_dir}.{filename[:-3]}"
            importlib.import_module(module_name)
