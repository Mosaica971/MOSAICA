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

    output_allocation = indicators.decode_output_allocation(model)
    input_allocation = indicators.decode_baseline_allocation(dataset)

    production_by_crop = indicators.compute_production_tonnes_by_crop(dataset, output_allocation)
    subsidy_by_crop = indicators.compute_subsidy_by_crop(dataset, output_allocation)
    total_revenue_by_crop = indicators.compute_total_revenue_by_crop(dataset, output_allocation)
    surface_by_region_output = indicators.compute_surface_by_region_and_key(dataset, output_allocation)
    surface_by_region_input = indicators.compute_surface_by_region_and_key(dataset, input_allocation)

    plots.plot_production_by_crop(production_by_crop, output_dir / "plots" / "production_by_crop.png")
    plots.plot_subsidy_by_crop(subsidy_by_crop, output_dir / "plots" / "subsidy_by_crop.png")
    plots.plot_revenue_by_crop(total_revenue_by_crop, output_dir / "plots" / "revenue_by_crop.png")
    plots.plot_surface_by_region(
        surface_by_region_output, output_dir / "plots" / "surface_by_region_output.png"
    )
    plots.plot_surface_by_region(
        surface_by_region_input, output_dir / "plots" / "surface_by_region_input.png"
    )

    _write_allocation_csv(dataset, output_allocation, output_dir / "allocation_output.csv")
    _write_allocation_csv(dataset, input_allocation, output_dir / "allocation_input.csv")

    output_summary = indicators.compute_aggregate_summary(dataset, output_allocation)
    input_summary = indicators.compute_aggregate_summary(dataset, input_allocation)
    delta_summary = {key: output_summary[key] - input_summary[key] for key in output_summary}

    gini_revenue_by_farm = _write_output_only_indicators(dataset, output_allocation, output_dir)
    _write_shannon_and_surface_by_key(
        dataset, input_allocation, output_allocation, output_dir
    )

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
    )
    (output_dir / "recap.json").write_text(json.dumps(recap, indent=2))
    (output_dir / "recap.md").write_text(_render_recap_markdown(recap))
    (output_dir / "config_used.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False)
    )

    return output_dir


def _write_output_only_indicators(
    dataset: Dataset, output_allocation: pd.Series, output_dir: Path
) -> float:
    """Indicators that need fine-crop-keyed price/yield data, so they can only be
    computed on the (84-crop) output allocation, not the (12-RPG-group) baseline --
    see VIGILANCE.md "Comparaison entree/sortie limitee a la resolution du groupe RPG"."""
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


def _write_shannon_and_surface_by_key(
    dataset: Dataset,
    input_allocation: pd.Series,
    output_allocation: pd.Series,
    output_dir: Path,
) -> None:
    """Indicators that only need surface data, so they're valid at both the input
    (12-group) and output (84-crop) resolution."""
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
        indicators.compute_surface_by_region_and_key(dataset, allocation).to_csv(
            output_dir / f"surface_by_region_{side}.csv", index_label="region"
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
        "termination_condition": results.termination_condition,
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
        "gini_revenue_by_farm": gini_revenue_by_farm,
        "total_plots": int(len(dataset.parameters["data_parc"])),
        "total_farms": int(dataset.parameters["expl_parc"]["farm"].nunique()),
    }


def _render_recap_markdown(recap: dict) -> str:
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
        "## Entree vs sortie",
        f"- Surface cultivee (ha) : {recap['input']['total_surface_ha']:.2f} -> "
        f"{recap['output']['total_surface_ha']:.2f} "
        f"(delta {recap['delta']['total_surface_ha']:+.2f})",
        f"- Parcelles actives : {recap['input']['active_plot_count']} -> "
        f"{recap['output']['active_plot_count']} "
        f"(delta {recap['delta']['active_plot_count']:+d})",
        f"- Exploitations actives : {recap['input']['farm_count']} -> "
        f"{recap['output']['farm_count']} "
        f"(delta {recap['delta']['farm_count']:+d})",
    ]
    return "\n".join(lines) + "\n"
