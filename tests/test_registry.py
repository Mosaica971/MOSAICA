import pytest

from core.model.registry import (
    CONSTRAINT_REGISTRY,
    OBJECTIVE_REGISTRY,
    register_constraint,
    register_objective,
)


def test_register_constraint_adds_function_to_constraint_registry():
    @register_constraint("test_dummy_constraint")
    def dummy(model, inputs, **args):
        return None

    try:
        assert CONSTRAINT_REGISTRY["test_dummy_constraint"] is dummy
    finally:
        del CONSTRAINT_REGISTRY["test_dummy_constraint"]


def test_register_constraint_raises_on_duplicate_name():
    @register_constraint("test_dummy_duplicate")
    def dummy(model, inputs, **args):
        return None

    try:
        with pytest.raises(ValueError, match="already registered"):

            @register_constraint("test_dummy_duplicate")
            def dummy2(model, inputs, **args):
                return None
    finally:
        del CONSTRAINT_REGISTRY["test_dummy_duplicate"]


def test_register_objective_adds_function_to_objective_registry():
    @register_objective("test_dummy_objective")
    def dummy(model, inputs, **args):
        return None

    try:
        assert OBJECTIVE_REGISTRY["test_dummy_objective"] is dummy
    finally:
        del OBJECTIVE_REGISTRY["test_dummy_objective"]


def test_register_objective_raises_on_duplicate_name():
    @register_objective("test_dummy_objective_duplicate")
    def dummy(model, inputs, **args):
        return None

    try:
        with pytest.raises(ValueError, match="already registered"):

            @register_objective("test_dummy_objective_duplicate")
            def dummy2(model, inputs, **args):
                return None
    finally:
        del OBJECTIVE_REGISTRY["test_dummy_objective_duplicate"]
