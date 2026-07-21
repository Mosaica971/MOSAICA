from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyomo.environ as pyo
import yaml

from case_studies.guadeloupe.domain import resilience
from case_studies.guadeloupe.pipeline.data_pipeline import DEFAULT_SCENARIO, DEFAULT_YEAR
from case_studies.guadeloupe.reporting import calibration, indicators, plots
from core.data.dataset import Dataset
from core.reporting.run_folder import create_output_folder


def _csv_path(output_dir: Path, name: str) -> Path:
    """Path for a run CSV, under output_dir/csv/ (created on demand). Non-CSV artifacts
    (recap.*, config_used.yaml) stay at the run root; plots live in output_dir/plots/."""
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    return csv_dir / name


def generate_report(
    dataset: Dataset,
    config: dict[str, Any],
    model: pyo.ConcreteModel,
    results: Any,
    duration: float,
    *,
    outputs_root: Path = Path("outputs"),
) -> Path:
    output_dir = create_output_folder(outputs_root)
    hours_per_etp = indicators.hours_per_etp_from_config(config)
    cost_per_hour = indicators.labor_cost_per_hour_from_config(config)

    output_allocation = indicators.decode_output_allocation(model)
    input_allocation = indicators.decode_baseline_allocation(dataset)
    # Input economics use a representative fine crop per aggregate baseline family, since
    # the observed 2017 baseline is only known at aggregate resolution (see VIGILANCE.md
    # "point 4"). Surface/diversity below stay on the raw aggregate baseline.
    input_representative = indicators.decode_baseline_representative_allocation(dataset, config)

    _write_allocation_csv(dataset, output_allocation, _csv_path(output_dir, "allocation_output.csv"))
    _write_allocation_csv(dataset, input_allocation, _csv_path(output_dir, "allocation_input.csv"))

    _write_crop_economics(dataset, output_allocation, output_dir, "output", cost_per_hour)
    _write_crop_economics(dataset, input_representative, output_dir, "input", cost_per_hour)
    # Tidy (crop x region) fact tables backing the comparison dashboard's free pivoting.
    for side, allocation in (("output", output_allocation), ("input", input_representative)):
        indicators.compute_facts_table(dataset, allocation, hours_per_etp, cost_per_hour).to_csv(
            _csv_path(output_dir, f"facts_{side}.csv"), index=False
        )
    _write_etp_indicators(dataset, output_allocation, hours_per_etp, output_dir, "output")
    _write_etp_indicators(dataset, input_representative, hours_per_etp, output_dir, "input")

    gini_revenue_by_farm = _write_output_only_indicators(dataset, output_allocation, output_dir)
    _write_shannon_and_surface_by_key(dataset, input_allocation, output_allocation, output_dir)

    calibration_result = calibration.evaluate(dataset, output_allocation, config)
    write_calibration(calibration_result, output_dir)

    output_summary = indicators.compute_aggregate_summary(dataset, output_allocation)
    input_summary = indicators.compute_aggregate_summary(dataset, input_allocation)
    delta_summary = {key: output_summary[key] - input_summary[key] for key in output_summary}

    output_econ = indicators.compute_economic_totals(
        dataset, output_allocation, hours_per_etp, cost_per_hour
    )
    input_econ = indicators.compute_economic_totals(
        dataset, input_representative, hours_per_etp, cost_per_hour
    )
    delta_econ = {key: output_econ[key] - input_econ[key] for key in output_econ}

    output_env = indicators.compute_environmental_totals(dataset, output_allocation)
    input_env = indicators.compute_environmental_totals(dataset, input_representative)
    delta_env = {key: output_env[key] - input_env[key] for key in output_env}

    output_auto = indicators.compute_food_autonomy_totals(dataset, output_allocation)
    input_auto = indicators.compute_food_autonomy_totals(dataset, input_representative)
    delta_auto = _numeric_delta(output_auto, input_auto)

    price_shock_delta = (config.get("resilience") or {}).get(
        "price_shock_delta", resilience.DEFAULT_PRICE_SHOCK_DELTA
    )
    output_res = indicators.compute_resilience_totals(
        dataset, output_allocation, price_shock_delta
    )
    input_res = indicators.compute_resilience_totals(
        dataset, input_representative, price_shock_delta
    )
    delta_res = {key: output_res[key] - input_res[key] for key in output_res}

    recap = _build_recap(
        dataset=dataset,
        config=config,
        results=results,
        duration=duration,
        objective_value=float(pyo.value(model.objective)),
        input_summary=input_summary,
        output_summary=output_summary,
        delta_summary=delta_summary,
        gini_revenue_by_farm=gini_revenue_by_farm,
        economics={"input": input_econ, "output": output_econ, "delta": delta_econ},
        environment={"input": input_env, "output": output_env, "delta": delta_env},
        food_autonomy={"input": input_auto, "output": output_auto, "delta": delta_auto},
        resilience={"input": input_res, "output": output_res, "delta": delta_res},
        calibration_summary=calibration_result.summary(),
    )
    # Full CULT_2017 universe (every fine crop the model could pick, allocated or not) so the
    # dashboard can show an exhaustive crop/subculture axis including never-chosen crops.
    recap["crop_universe"] = sorted(dataset.sets.get("crops", []))
    (output_dir / "recap.json").write_text(json.dumps(recap, indent=2))
    (output_dir / "recap.md").write_text(_render_recap_markdown(recap))
    (output_dir / "config_used.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
    )

    return output_dir


def _write_crop_economics(
    dataset: Dataset, allocation: pd.Series, output_dir: Path, side: str, cost_per_hour: float
) -> None:
    """Per-crop production (tonnes), subsidy, revenue, gross margin and labor cost (EUR) for
    one side, with a figure each. `side` is "output" (fine solved crops) or "input"
    (representative baseline crops -- see decode_baseline_representative_allocation)."""
    production = indicators.compute_production_tonnes_by_crop(dataset, allocation)
    subsidy = indicators.compute_subsidy_by_crop(dataset, allocation)
    revenue = indicators.compute_total_revenue_by_crop(dataset, allocation)
    gross_margin = indicators.compute_gross_margin_by_crop(dataset, allocation)
    labor_cost = indicators.compute_labor_cost_by_crop(dataset, allocation, cost_per_hour)

    production.to_csv(
        _csv_path(output_dir, f"production_by_crop_{side}.csv"),
        header=["production_tonnes"], index_label="crop",
    )
    subsidy.to_csv(_csv_path(output_dir, f"subsidy_by_crop_{side}.csv"), header=["subsidy"], index_label="crop")
    revenue.to_csv(_csv_path(output_dir, f"revenue_by_crop_{side}.csv"), header=["revenue"], index_label="crop")
    gross_margin.to_csv(
        _csv_path(output_dir, f"gross_margin_by_crop_{side}.csv"),
        header=["gross_margin"], index_label="crop",
    )
    labor_cost.to_csv(
        _csv_path(output_dir, f"labor_cost_by_crop_{side}.csv"),
        header=["labor_cost"], index_label="crop",
    )

    plots.plot_production_by_crop(production, output_dir / "plots" / f"production_by_crop_{side}.png")
    plots.plot_subsidy_by_crop(subsidy, output_dir / "plots" / f"subsidy_by_crop_{side}.png")
    plots.plot_revenue_by_crop(revenue, output_dir / "plots" / f"revenue_by_crop_{side}.png")
    plots.plot_gross_margin_by_crop(gross_margin, output_dir / "plots" / f"gross_margin_by_crop_{side}.png")
    plots.plot_labor_cost_by_crop(labor_cost, output_dir / "plots" / f"labor_cost_by_crop_{side}.png")


def _write_output_only_indicators(
    dataset: Dataset, output_allocation: pd.Series, output_dir: Path
) -> float:
    """Ratios and per-farm revenue that only make sense on the fine (84-crop) output
    allocation. Per-farm revenue needs a per-plot crop, and the ratios need fine-crop
    yields; the aggregate baseline has neither, so these stay output-only."""
    indicators.compute_subsidy_per_tonne_by_crop(dataset, output_allocation).to_csv(
        _csv_path(output_dir, "subsidy_per_tonne_by_crop.csv"),
        header=["subsidy_per_tonne"], index_label="crop",
    )
    indicators.compute_subsidy_per_euro_sold_by_crop(dataset, output_allocation).to_csv(
        _csv_path(output_dir, "subsidy_per_euro_sold_by_crop.csv"),
        header=["subsidy_per_euro_sold"],
        index_label="crop",
    )

    revenue_by_farm = indicators.compute_revenue_by_farm(dataset, output_allocation)
    revenue_by_farm.to_csv(
        _csv_path(output_dir, "revenue_by_farm.csv"), header=["revenue"], index_label="farm"
    )
    return indicators.compute_gini(revenue_by_farm)


def _write_etp_indicators(
    dataset: Dataset, allocation: pd.Series, hours_per_etp: float, output_dir: Path, side: str
) -> None:
    """Employment (ETP / full-time equivalents) by region/island/farm for one side, from
    the labor hours embedded in each crop's technical itinerary."""
    region = indicators.plot_to_region(dataset)
    island = indicators.plot_to_island(dataset)
    farm = indicators.plot_to_farm(dataset)

    etp_by_region = indicators.compute_etp_by_key(dataset, allocation, region, hours_per_etp)
    indicators.compute_etp_by_key(dataset, allocation, island, hours_per_etp).to_csv(
        _csv_path(output_dir, f"etp_by_island_{side}.csv"), header=["etp"], index_label="island"
    )
    indicators.compute_etp_by_key(dataset, allocation, farm, hours_per_etp).to_csv(
        _csv_path(output_dir, f"etp_by_farm_{side}.csv"), header=["etp"], index_label="farm"
    )
    etp_by_region.to_csv(
        _csv_path(output_dir, f"etp_by_region_{side}.csv"), header=["etp"], index_label="region"
    )
    plots.plot_etp_by_region(etp_by_region, output_dir / "plots" / f"etp_by_region_{side}.png")


def _write_shannon_and_surface_by_key(
    dataset: Dataset,
    input_allocation: pd.Series,
    output_allocation: pd.Series,
    output_dir: Path,
) -> None:
    """Surface-only indicators (Shannon diversity + surface by region/island), valid at
    both the raw aggregate baseline and the fine output resolution."""
    region = indicators.plot_to_region(dataset)
    island = indicators.plot_to_island(dataset)
    for side, allocation in (("input", input_allocation), ("output", output_allocation)):
        indicators.compute_shannon_diversity(dataset, allocation, region).to_csv(
            _csv_path(output_dir, f"shannon_diversity_by_region_{side}.csv"),
            header=["shannon_diversity"],
            index_label="region",
        )
        indicators.compute_shannon_diversity(dataset, allocation, island).to_csv(
            _csv_path(output_dir, f"shannon_diversity_by_island_{side}.csv"),
            header=["shannon_diversity"],
            index_label="island",
        )
        surface_by_region = indicators.compute_surface_by_region_and_key(dataset, allocation)
        surface_by_region.to_csv(
            _csv_path(output_dir, f"surface_by_region_{side}.csv"), index_label="region"
        )
        plots.plot_surface_by_region(
            surface_by_region, output_dir / "plots" / f"surface_by_region_{side}.png"
        )
        indicators.compute_surface_by_island_and_key(dataset, allocation).to_csv(
            _csv_path(output_dir, f"surface_by_island_{side}.csv"), index_label="island"
        )


def write_calibration(result: calibration.CalibrationResult, output_dir: Path) -> None:
    """Persist the observed-vs-simulated calibration blocks (Chopin et al. 2015 §2.6).

    Public because scripts/evaluate_calibration.py writes the same files into a past run's
    folder. Reporting only: these numbers grade the run, they never feed back into it.
    """
    result.pad_by_crop.to_csv(_csv_path(output_dir, "calibration_pad_by_crop.csv"))
    result.pad_by_crop_and_region.to_csv(
        _csv_path(output_dir, "calibration_pad_by_crop_and_region.csv")
    )
    result.pad_by_farm.to_csv(_csv_path(output_dir, "calibration_pad_by_farm.csv"))
    result.farm_type_confusion.to_csv(
        _csv_path(output_dir, "calibration_farm_type_confusion.csv")
    )
    result.field_match.to_csv(_csv_path(output_dir, "calibration_field_match.csv"))

    plots.plot_calibration_regional(
        result.pad_by_crop, output_dir / "plots" / "calibration_regional.png"
    )
    plots.plot_calibration_pad_heatmap(
        result.pad_by_crop_and_region, output_dir / "plots" / "calibration_pad_heatmap.png"
    )


def _write_allocation_csv(dataset: Dataset, allocation: pd.Series, path: Path) -> None:
    data_parc = dataset.parameters["data_parc"]
    farm = indicators.plot_to_farm(dataset).reindex(allocation.index)
    frame = pd.DataFrame(
        {
            "plot": allocation.index,
            "crop": allocation.to_numpy(),
            "farm": farm.to_numpy(),
            "region": data_parc["REGION"].reindex(allocation.index).to_numpy(),
            "island": data_parc["ILE"].reindex(allocation.index).to_numpy(),
            "surface_ha": data_parc["SURF_HA"].reindex(allocation.index).to_numpy(),
        }
    )
    frame.to_csv(path, index=False)


def _numeric_delta(output: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """Recursive output-minus-baseline over a nested dict of numbers (one level of nested
    dicts, e.g. food_autonomy's crop_only/with_fishing sub-dicts)."""
    delta: dict[str, Any] = {}
    for key, out_value in output.items():
        base_value = baseline[key]
        if isinstance(out_value, dict):
            delta[key] = _numeric_delta(out_value, base_value)
        else:
            delta[key] = out_value - base_value
    return delta


def _build_recap(
    *,
    dataset: Dataset,
    config: dict[str, Any],
    results: Any,
    duration: float,
    objective_value: float,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    delta_summary: dict[str, Any],
    gini_revenue_by_farm: float,
    economics: dict[str, Any],
    environment: dict[str, Any],
    food_autonomy: dict[str, Any],
    resilience: dict[str, Any],
    calibration_summary: dict[str, Any],
) -> dict[str, Any]:
    enabled_constraints = [
        {"name": entry["name"], "args": entry.get("args") or {}}
        for entry in config["constraints"]
        if entry.get("enable", False)
    ]
    enabled_objective = next(entry for entry in config["objectives"] if entry.get("enable", False))
    data_cfg = config.get("data", {})
    return {
        # Set by the scenario batch runner (scripts/run_scenarios.py); None for a plain
        # single run via main.py. Lets the dashboard label runs by their scenario name.
        "run_name": config.get("run_name"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "solve_duration_seconds": duration,
        "termination_condition": str(results.solver.termination_condition),
        "solver": config["solver"],
        # Which economic year and scenario produced this run (see data_pipeline.build_dataset).
        "data": {
            "year": data_cfg.get("year", DEFAULT_YEAR),
            "scenario": data_cfg.get("scenario", DEFAULT_SCENARIO),
        },
        "objective": {
            "name": enabled_objective["name"],
            "args": enabled_objective.get("args") or {},
            "value": objective_value,
        },
        "constraints": enabled_constraints,
        "input": input_summary,
        "output": output_summary,
        "delta": delta_summary,
        "economics": economics,
        "environment": environment,
        "food_autonomy": food_autonomy,
        "resilience": resilience,
        # How close this run's allocation lands to the observed 2017 land use
        # (Chopin et al. 2015 §2.6) -- a report card, never an input to the model.
        "calibration": calibration_summary,
        "gini_revenue_by_farm": gini_revenue_by_farm,
        "total_plots": int(len(dataset.parameters["data_parc"])),
        "total_farms": int(dataset.parameters["expl_parc"]["farm"].nunique()),
    }


def _render_recap_markdown(recap: dict[str, Any]) -> str:
    econ = recap["economics"]
    lines = [
        "# Recap de simulation",
        "",
        *([f"- Scenario : {recap['run_name']}"] if recap.get("run_name") else []),
        f"- Horodatage : {recap['timestamp']}",
        f"- Duree de resolution : {recap['solve_duration_seconds']:.2f}s",
        f"- Condition de terminaison : {recap['termination_condition']}",
        f"- Solveur : {recap['solver']['name']}",
        f"- Annee / scenario : {recap['data']['year']} / {recap['data']['scenario']}",
        f"- Nombre de parcelles (total) : {recap['total_plots']}",
        f"- Nombre d'exploitations (total) : {recap['total_farms']}",
        "",
        "## Objectif",
        f"- {recap['objective']['name']} = {recap['objective']['value']:,.2f}",
        "",
        "## Contraintes activees",
    ]
    for constraint in recap["constraints"]:
        lines.append(f"- {constraint['name']} {constraint['args']}")
    lines += [
        "",
        "## Entree vs sortie (surface)",
        f"- Surface cultivee (ha) : {recap['input']['total_surface_ha']:.2f} -> "
        f"{recap['output']['total_surface_ha']:.2f} "
        f"(delta {recap['delta']['total_surface_ha']:+.2f})",
        f"- Parcelles actives : {recap['input']['active_plot_count']} -> "
        f"{recap['output']['active_plot_count']} "
        f"(delta {recap['delta']['active_plot_count']:+d})",
        f"- Exploitations actives : {recap['input']['farm_count']} -> "
        f"{recap['output']['farm_count']} "
        f"(delta {recap['delta']['farm_count']:+d})",
        "",
        "## Entree vs sortie (economie)",
        "_Entree = baseline 2017 a economie representative par famille (voir VIGILANCE.md point 4)._",
        f"- Production (t) : {econ['input']['total_production_tonnes']:,.0f} -> "
        f"{econ['output']['total_production_tonnes']:,.0f} "
        f"(delta {econ['delta']['total_production_tonnes']:+,.0f})",
        f"- Subvention (EUR) : {econ['input']['total_subsidy']:,.0f} -> "
        f"{econ['output']['total_subsidy']:,.0f} (delta {econ['delta']['total_subsidy']:+,.0f})",
        f"- Revenu / produit brut (EUR) : {econ['input']['total_revenue']:,.0f} -> "
        f"{econ['output']['total_revenue']:,.0f} (delta {econ['delta']['total_revenue']:+,.0f})",
        f"- Cout variable (EUR) : {econ['input']['total_variable_cost']:,.0f} -> "
        f"{econ['output']['total_variable_cost']:,.0f} (delta {econ['delta']['total_variable_cost']:+,.0f})",
        f"- Marge brute (EUR) : {econ['input']['total_gross_margin']:,.0f} -> "
        f"{econ['output']['total_gross_margin']:,.0f} (delta {econ['delta']['total_gross_margin']:+,.0f})",
        f"- Cout main d'oeuvre (EUR) : {econ['input']['total_labor_cost']:,.0f} -> "
        f"{econ['output']['total_labor_cost']:,.0f} (delta {econ['delta']['total_labor_cost']:+,.0f})",
        f"- Revenu net (marge brute - cout MO, EUR) : {econ['input']['total_net_revenue']:,.0f} -> "
        f"{econ['output']['total_net_revenue']:,.0f} (delta {econ['delta']['total_net_revenue']:+,.0f})",
        f"- Emploi (ETP) : {econ['input']['total_etp']:,.1f} -> "
        f"{econ['output']['total_etp']:,.1f} (delta {econ['delta']['total_etp']:+,.1f})",
    ]

    calib = recap["calibration"]

    def _verdict(passed: bool) -> str:
        return "OK" if passed else "HORS SEUIL"

    def _pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value:,.1f}%"

    lines += [
        "",
        "## Calibration (observe 2017 vs simule)",
        "_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015"
        " section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._",
        f"- PAD territorial : {_pct(calib['regional_pad_pct'])} "
        f"(seuil {calib['thresholds']['regional_pad_max']:.0f}%) "
        f"-> {_verdict(calib['regional_within_threshold'])}",
        f"- Cultures sous seuil : {calib['crops_within_threshold']} / {calib['crops_evaluated']}",
        f"- Cellules sous-regionales sous seuil : "
        f"{calib['subregional_cells_within_threshold']} / {calib['subregional_cells_evaluated']} "
        f"(seuil {calib['thresholds']['subregional_pad_max']:.0f}%)",
        f"- Exploitations sous seuil : {calib['farms_within_threshold']} / "
        f"{calib['farms_evaluated']} (seuil {calib['thresholds']['farm_pad_max']:.0f}%)",
        f"- Types d'exploitation correctement simules : {_pct(calib['farm_type_match_pct'])} "
        f"(seuil {calib['thresholds']['farm_type_match_min']:.0f}%) "
        f"-> {_verdict(calib['farm_type_within_threshold'])}",
        f"- Parcelles avec la bonne culture : {_pct(calib['plot_match_pct'])} "
        f"({calib['matched_plots']} / {calib['total_plots']})",
        f"- Surface avec la bonne culture : {_pct(calib['area_match_pct'])} "
        f"({calib['matched_ha']:,.0f} / {calib['total_ha']:,.0f} ha)",
    ]
    return "\n".join(lines) + "\n"
