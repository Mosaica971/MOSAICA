from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyomo.environ as pyo
import yaml

from case_studies.guadeloupe.reporting import indicators, plots
from core.data.dataset import Dataset
from core.reporting.run_folder import create_output_folder


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

    output_allocation = indicators.decode_output_allocation(model)
    input_allocation = indicators.decode_baseline_allocation(dataset)
    # Input economics use a representative fine crop per aggregate baseline family, since
    # the observed 2017 baseline is only known at aggregate resolution (see VIGILANCE.md
    # "point 4"). Surface/diversity below stay on the raw aggregate baseline.
    input_representative = indicators.decode_baseline_representative_allocation(dataset, config)

    _write_allocation_csv(dataset, output_allocation, output_dir / "allocation_output.csv")
    _write_allocation_csv(dataset, input_allocation, output_dir / "allocation_input.csv")

    _write_crop_economics(dataset, output_allocation, output_dir, "output")
    _write_crop_economics(dataset, input_representative, output_dir, "input")
    _write_etp_indicators(dataset, output_allocation, hours_per_etp, output_dir, "output")
    _write_etp_indicators(dataset, input_representative, hours_per_etp, output_dir, "input")

    gini_revenue_by_farm = _write_output_only_indicators(dataset, output_allocation, output_dir)
    _write_shannon_and_surface_by_key(dataset, input_allocation, output_allocation, output_dir)

    output_summary = indicators.compute_aggregate_summary(dataset, output_allocation)
    input_summary = indicators.compute_aggregate_summary(dataset, input_allocation)
    delta_summary = {key: output_summary[key] - input_summary[key] for key in output_summary}

    output_econ = indicators.compute_economic_totals(dataset, output_allocation, hours_per_etp)
    input_econ = indicators.compute_economic_totals(dataset, input_representative, hours_per_etp)
    delta_econ = {key: output_econ[key] - input_econ[key] for key in output_econ}

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
    )
    (output_dir / "recap.json").write_text(json.dumps(recap, indent=2))
    (output_dir / "recap.md").write_text(_render_recap_markdown(recap))
    (output_dir / "config_used.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
    )

    return output_dir


def _write_crop_economics(
    dataset: Dataset, allocation: pd.Series, output_dir: Path, side: str
) -> None:
    """Per-crop production (tonnes), subsidy (EUR) and revenue (EUR) for one side, with a
    figure each. `side` is "output" (fine solved crops) or "input" (representative
    baseline crops -- see decode_baseline_representative_allocation)."""
    production = indicators.compute_production_tonnes_by_crop(dataset, allocation)
    subsidy = indicators.compute_subsidy_by_crop(dataset, allocation)
    revenue = indicators.compute_total_revenue_by_crop(dataset, allocation)

    production.to_csv(
        output_dir / f"production_by_crop_{side}.csv", header=["production_tonnes"], index_label="crop"
    )
    subsidy.to_csv(output_dir / f"subsidy_by_crop_{side}.csv", header=["subsidy"], index_label="crop")
    revenue.to_csv(output_dir / f"revenue_by_crop_{side}.csv", header=["revenue"], index_label="crop")

    plots.plot_production_by_crop(production, output_dir / "plots" / f"production_by_crop_{side}.png")
    plots.plot_subsidy_by_crop(subsidy, output_dir / "plots" / f"subsidy_by_crop_{side}.png")
    plots.plot_revenue_by_crop(revenue, output_dir / "plots" / f"revenue_by_crop_{side}.png")


def _write_output_only_indicators(
    dataset: Dataset, output_allocation: pd.Series, output_dir: Path
) -> float:
    """Ratios and per-farm revenue that only make sense on the fine (84-crop) output
    allocation. Per-farm revenue needs a per-plot crop, and the ratios need fine-crop
    yields; the aggregate baseline has neither, so these stay output-only."""
    indicators.compute_subsidy_per_tonne_by_crop(dataset, output_allocation).to_csv(
        output_dir / "subsidy_per_tonne_by_crop.csv", header=["subsidy_per_tonne"], index_label="crop"
    )
    indicators.compute_subsidy_per_euro_sold_by_crop(dataset, output_allocation).to_csv(
        output_dir / "subsidy_per_euro_sold_by_crop.csv",
        header=["subsidy_per_euro_sold"],
        index_label="crop",
    )

    revenue_by_farm = indicators.compute_revenue_by_farm(dataset, output_allocation)
    revenue_by_farm.to_csv(
        output_dir / "revenue_by_farm.csv", header=["revenue"], index_label="farm"
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
        output_dir / f"etp_by_island_{side}.csv", header=["etp"], index_label="island"
    )
    indicators.compute_etp_by_key(dataset, allocation, farm, hours_per_etp).to_csv(
        output_dir / f"etp_by_farm_{side}.csv", header=["etp"], index_label="farm"
    )
    etp_by_region.to_csv(
        output_dir / f"etp_by_region_{side}.csv", header=["etp"], index_label="region"
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
            output_dir / f"shannon_diversity_by_region_{side}.csv",
            header=["shannon_diversity"],
            index_label="region",
        )
        indicators.compute_shannon_diversity(dataset, allocation, island).to_csv(
            output_dir / f"shannon_diversity_by_island_{side}.csv",
            header=["shannon_diversity"],
            index_label="island",
        )
        surface_by_region = indicators.compute_surface_by_region_and_key(dataset, allocation)
        surface_by_region.to_csv(output_dir / f"surface_by_region_{side}.csv", index_label="region")
        plots.plot_surface_by_region(
            surface_by_region, output_dir / "plots" / f"surface_by_region_{side}.png"
        )
        indicators.compute_surface_by_island_and_key(dataset, allocation).to_csv(
            output_dir / f"surface_by_island_{side}.csv", index_label="island"
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


def _build_recap(
    *,
    dataset: Dataset,
    config: dict[str, Any],
    results: Any,
    duration: float,
    objective_value: float,
    input_summary: dict,
    output_summary: dict,
    delta_summary: dict,
    gini_revenue_by_farm: float,
    economics: dict,
) -> dict:
    enabled_constraints = [
        {"name": entry["name"], "args": entry.get("args") or {}}
        for entry in config["constraints"]
        if entry.get("enable", False)
    ]
    enabled_objective = next(entry for entry in config["objectives"] if entry.get("enable", False))
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "solve_duration_seconds": duration,
        "termination_condition": str(results.solver.termination_condition),
        "solver": config["solver"],
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
        "gini_revenue_by_farm": gini_revenue_by_farm,
        "total_plots": int(len(dataset.parameters["data_parc"])),
        "total_farms": int(dataset.parameters["expl_parc"]["farm"].nunique()),
    }


def _render_recap_markdown(recap: dict) -> str:
    econ = recap["economics"]
    lines = [
        "# Recap de simulation",
        "",
        f"- Horodatage : {recap['timestamp']}",
        f"- Duree de resolution : {recap['solve_duration_seconds']:.2f}s",
        f"- Condition de terminaison : {recap['termination_condition']}",
        f"- Solveur : {recap['solver']['name']}",
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
        f"- Revenu (EUR) : {econ['input']['total_revenue']:,.0f} -> "
        f"{econ['output']['total_revenue']:,.0f} (delta {econ['delta']['total_revenue']:+,.0f})",
        f"- Emploi (ETP) : {econ['input']['total_etp']:,.1f} -> "
        f"{econ['output']['total_etp']:,.1f} (delta {econ['delta']['total_etp']:+,.1f})",
    ]
    return "\n".join(lines) + "\n"
