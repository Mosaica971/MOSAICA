"""Warm start: writing an allocation into the model and auditing it. No data, no solve."""

import pyomo.environ as pyo
import pytest

from core.model.warm_start import (
    apply_allocation,
    constraint_violations,
    objective_value,
)

PAIRS = [("p1", "cane"), ("p1", "pasture"), ("p2", "cane"), ("p2", "pasture")]


def build_model(pairs=PAIRS) -> pyo.ConcreteModel:
    """Two plots, two crops, at most one crop each, maximise a margin. Deliberately tiny."""
    model = pyo.ConcreteModel()
    model.PAIRS = pyo.Set(initialize=pairs, dimen=2)
    model.PLOTS = pyo.Set(initialize=sorted({plot for plot, _ in pairs}))
    model.Y = pyo.Var(model.PAIRS, within=pyo.Binary)

    plots_to_crops: dict[str, list[str]] = {}
    for plot, crop in pairs:
        plots_to_crops.setdefault(plot, []).append(crop)

    model.one_crop = pyo.Constraint(
        model.PLOTS,
        rule=lambda m, plot: sum(m.Y[plot, crop] for crop in plots_to_crops[plot]) <= 1,
    )
    margin = {"cane": 10.0, "pasture": 4.0}
    model.objective = pyo.Objective(
        expr=sum(model.Y[plot, crop] * margin[crop] for plot, crop in pairs),
        sense=pyo.maximize,
    )
    return model


def test_apply_allocation_writes_a_complete_zero_one_vector():
    model = build_model()

    report = apply_allocation(model, {"p1": "cane", "p2": "pasture"})

    assert report.assigned == 2
    assert report.dropped == []
    assert report.plots_left_empty == 0
    # Every variable is written, zeros included -- HiGHS reads the whole column vector.
    assert model.Y["p1", "cane"].value == 1.0
    assert model.Y["p1", "pasture"].value == 0.0
    assert model.Y["p2", "cane"].value == 0.0
    assert model.Y["p2", "pasture"].value == 1.0


def test_apply_allocation_skips_pairs_the_model_does_not_carry():
    # The source run's eligibility mask differed: it put melon on p1, which is not a
    # variable here. Skipping beats raising -- the rest of the allocation is still useful.
    model = build_model()

    report = apply_allocation(model, {"p1": "melon", "p2": "cane"})

    assert report.assigned == 1
    assert report.dropped == [("p1", "melon")]
    assert report.plots_left_empty == 1
    assert model.Y["p1", "cane"].value == 0.0
    assert model.Y["p1", "pasture"].value == 0.0


def test_apply_allocation_leaves_unmentioned_plots_empty():
    model = build_model()

    report = apply_allocation(model, {"p1": "cane"})

    assert report.plots_left_empty == 1
    assert model.Y["p2", "cane"].value == 0.0


def test_constraint_violations_empty_on_a_feasible_allocation():
    model = build_model()
    apply_allocation(model, {"p1": "cane", "p2": "pasture"})

    assert constraint_violations(model) == []


def test_constraint_violations_reports_amount_and_worst_first():
    model = build_model()
    apply_allocation(model, {})
    # Force both crops onto p1: the one-crop-per-plot constraint is violated by 1.
    model.Y["p1", "cane"].set_value(1.0)
    model.Y["p1", "pasture"].set_value(1.0)

    violations = constraint_violations(model)

    assert len(violations) == 1
    name, amount = violations[0]
    assert "one_crop" in name
    assert amount == pytest.approx(1.0)


def test_constraint_violations_flags_an_unevaluable_start_as_infinite():
    # A variable left at None cannot be evaluated; reporting it as feasible would be the
    # dangerous answer, so it is reported as an infinite violation instead.
    model = build_model()

    violations = constraint_violations(model)

    assert violations
    assert all(amount == float("inf") for _, amount in violations)


def test_objective_value_reads_the_incumbent_being_handed_over():
    model = build_model()
    apply_allocation(model, {"p1": "cane", "p2": "pasture"})

    assert objective_value(model) == pytest.approx(14.0)
