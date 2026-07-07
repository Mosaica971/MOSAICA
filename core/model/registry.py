from collections.abc import Callable
from typing import TypeVar

F = TypeVar("F", bound=Callable)

CONSTRAINT_REGISTRY: dict[str, Callable] = {}
OBJECTIVE_REGISTRY: dict[str, Callable] = {}


def _make_register(registry: dict[str, Callable]) -> Callable[[str], Callable[[F], F]]:
    def register(name: str) -> Callable[[F], F]:
        def decorator(fn: F) -> F:
            if name in registry:
                raise ValueError(f"'{name}' is already registered")
            registry[name] = fn
            return fn

        return decorator

    return register


register_constraint = _make_register(CONSTRAINT_REGISTRY)
register_objective = _make_register(OBJECTIVE_REGISTRY)
