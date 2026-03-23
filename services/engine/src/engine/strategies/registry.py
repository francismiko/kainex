from typing import TypeVar

from engine.strategies.base import AbstractStrategy

T = TypeVar("T", bound=AbstractStrategy)


class StrategyRegistry:
    """Discovers and manages strategy classes."""

    def __init__(self) -> None:
        self._strategies: dict[str, type[AbstractStrategy]] = {}

    def register(self, strategy_cls: type[T]) -> type[T]:
        """Register a strategy class. Can be used as a decorator."""
        self._strategies[strategy_cls.name] = strategy_cls
        return strategy_cls

    def get(self, name: str) -> type[AbstractStrategy]:
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not registered")
        return self._strategies[name]

    def list_strategies(self) -> list[str]:
        return list(self._strategies.keys())

    def create(self, name: str, **kwargs) -> AbstractStrategy:
        cls = self.get(name)
        return cls(**kwargs)


registry = StrategyRegistry()
