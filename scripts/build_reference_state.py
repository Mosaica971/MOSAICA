"""Build the 2017 reference state of Guadeloupe -- the observed situation every run is
scored against.

    python scripts/build_reference_state.py            # -> outputs/reference_2017/
    python scripts/build_reference_state.py --dir <path>

No solve: the reference is read straight out of the RPG land-use history in
Data_Parc_Gwad_2017.txt (~5 s). It is deliberately built with the SAME functions the model
and the calibration use -- decode_baseline_allocation, compute_base_crop_group,
compute_type_expl, indicators.* -- so the reference folder and a run's "input" side are the
same numbers by construction, not two parallel reconstructions that could drift apart.

Four things make this more than a group-by, and each has its own CSV:

1. RAW vs RESOLVED land use. GAMS forces cult_2017 to NC when cult_2016 AND cult_2017 are
   both fallow (ENTREES.txt:49-57). That moves ~1200 ha from JA to NC before anything else
   happens. Both readings are written out, so the reclassification is visible rather than
   implicit.
2. THE OBSERVED SIDE HAS NO FINE CROPS. The 12 RPG groups say "sugarcane", never which
   technical system. Every economic/environmental figure of the reference therefore rests on
   config's baseline_representative_crops. The central estimate uses exactly that assumption
   (so it matches the runs); a low/high bracket over the fine variants each plot could
   actually carry says how much the assumption is worth.
3. THE REPRODUCIBILITY CEILING. Part of the observed acreage sits on plots where no fine
   variant of the observed family is eligible -- the model cannot reproduce it whatever the
   objective does. That share is a floor under the PAD, and it belongs to the reference, not
   to the run.
4. THE FARM TYPOLOGY. The observed TYPE_EXPL distribution is the row-marginal of every
   confusion matrix, and it also fixes each farm's risk aversion, so it is part of the
   reference state and not a result.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from case_studies.guadeloupe.domain import crop_families
from case_studies.guadeloupe.domain.farm_typology import (
    TYPE_EXPL_LABELS,
    compute_avers,
    compute_base_crop_group,
    compute_type_expl,
)
from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from case_studies.guadeloupe.reporting import indicators
from core.config import load_config
from core.data.dataset import Dataset

from scripts._common import CONFIG_PATH, OUTPUTS_ROOT, format_number as _n

DEFAULT_DIR_NAME = "reference_2017"

# Readable names for the 12 observed RPG groups (ENTREES.txt:62-103). ASCII only, like
# crop_labels.py: these reach a markdown file that carries no accents.
GROUP_LABELS: dict[str, str] = {
    "AG": "Agrumes",
    "AN": "Ananas",
    "BA": "Banane export",
    "BC": "Banane plantain",
    "CS": "Canne a sucre",
    "IG": "Igname et tubercules",
    "JA": "Jachere",
    "MA": "Maraichage",
    "ME": "Melon",
    "NC": "Non cultive",
    "PN": "Prairies et savanes",
    "VE": "Vergers hors agrumes",
}

# Per-ha rates bracketed below. Each entry is (metric name, dataset parameter or None for a
# metric derived in _metric_rates).
_BRACKETED_METRICS = (
    "production_tonnes",
    "sales",
    "subsidy",
    "revenue",
    "gross_margin",
    "labor_hours",
    "azote",
    "ges",
    "ift",
)


def _raw_groups(data_parc: pd.DataFrame) -> pd.Series:
    """plot -> RPG group read from cult_2017 alone, WITHOUT the fallow-continuity rule.

    Obtained by handing compute_base_crop_group a cult_2016 that is never fallow, so the
    rule cannot fire -- rather than duplicating the code->group table here, which would be
    one more place to keep in sync with ENTREES.txt.
    """
    never_fallow = pd.Series(1, index=data_parc.index)
    return compute_base_crop_group(never_fallow, data_parc["cult_2017"])


def _resolved_groups(data_parc: pd.DataFrame) -> pd.Series:
    """plot -> RPG group as the model reads it: the fallow-continuity rule applied, NC kept."""
    return compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])


def _surface_and_count(surface: pd.Series, groups: pd.Series) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "surface_ha": surface.reindex(groups.index).groupby(groups).sum(),
            "parcelles": groups.groupby(groups).size(),
        }
    )
    return frame


def land_use_table(dataset: Dataset) -> pd.DataFrame:
    """Observed acreage per RPG group, in the two readings plus the cultivated reference.

    `retenu_ha` is what the PAD is computed against: the resolved reading minus NC, since a
    non-cultivated plot is not part of any crop's acreage on either side.
    """
    data_parc = dataset.parameters["data_parc"]
    surface = data_parc["SURF_HA"]
    raw = _surface_and_count(surface, _raw_groups(data_parc))
    resolved = _surface_and_count(surface, _resolved_groups(data_parc))

    frame = pd.DataFrame(
        {
            "libelle": pd.Series(GROUP_LABELS),
            "brut_ha": raw["surface_ha"],
            "brut_parcelles": raw["parcelles"],
            "resolu_ha": resolved["surface_ha"],
            "resolu_parcelles": resolved["parcelles"],
        }
    ).fillna({"brut_ha": 0.0, "brut_parcelles": 0, "resolu_ha": 0.0, "resolu_parcelles": 0})
    frame["ecart_resolution_ha"] = frame["resolu_ha"] - frame["brut_ha"]
    frame["retenu_ha"] = frame["resolu_ha"].where(frame.index != crop_families.NON_CULTIVATED, 0.0)
    cultivated = float(frame["retenu_ha"].sum())
    frame["part_cultive_pct"] = 100.0 * frame["retenu_ha"] / cultivated
    frame.index.name = "groupe"
    return frame.sort_index()


def surface_by_group_and_key(
    dataset: Dataset, groups: pd.Series, key: pd.Series, key_name: str
) -> pd.DataFrame:
    """Cultivated reference acreage pivoted as key x group, with row and column totals."""
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(groups.index)
    frame = pd.DataFrame(
        {key_name: key.reindex(groups.index), "groupe": groups, "surface_ha": surface}
    )
    pivot = frame.pivot_table(
        index=key_name, columns="groupe", values="surface_ha", aggfunc="sum", fill_value=0.0
    )
    pivot["TOTAL"] = pivot.sum(axis=1)
    pivot.loc["TOTAL"] = pivot.sum(axis=0)
    return pivot.round(2)


def farm_typology_table(dataset: Dataset) -> pd.DataFrame:
    """Observed farm-type distribution: the row-marginal of every confusion matrix, and the
    table that fixes each farm's risk aversion (AVERS) in the Markowitz objective."""
    data_parc = dataset.parameters["data_parc"]
    type_expl, type_bis = compute_type_expl(
        dataset.parameters["farm_plots"], _resolved_groups(data_parc), data_parc["SURF_HA"]
    )
    avers = compute_avers(type_expl, type_bis)
    farm_surface = dataset.parameters["farm_surface_ha"]

    frame = pd.DataFrame(
        {
            "exploitations": type_expl.groupby(type_expl).size(),
            "surface_ha": farm_surface.reindex(type_expl.index).groupby(type_expl).sum(),
            "avers_min": avers.groupby(type_expl).min(),
            "avers_max": avers.groupby(type_expl).max(),
        }
    )
    frame.insert(0, "libelle", pd.Series({code: TYPE_EXPL_LABELS[code] for code in frame.index}))
    frame["part_exploitations_pct"] = 100.0 * frame["exploitations"] / frame["exploitations"].sum()
    frame.index.name = "type_expl"
    return frame


def reference_allocation(dataset: Dataset, config: dict[str, Any]) -> pd.DataFrame:
    """The canonical per-plot reference: what was observed there in 2017, and which fine
    crop stands in for it when a per-ha rate is needed."""
    data_parc = dataset.parameters["data_parc"]
    resolved = _resolved_groups(data_parc)
    representative = indicators.decode_baseline_representative_allocation(dataset, config)
    farm = indicators.plot_to_farm(dataset)

    frame = pd.DataFrame(
        {
            "plot": data_parc.index,
            "farm": farm.reindex(data_parc.index).to_numpy(),
            "region": data_parc["REGION"].to_numpy(),
            "island": data_parc["ILE"].to_numpy(),
            "commune": data_parc["COMMUNE"].to_numpy(),
            "surface_ha": data_parc["SURF_HA"].to_numpy(),
            "code_cult_2016": data_parc["cult_2016"].to_numpy(),
            "code_cult_2017": data_parc["cult_2017"].to_numpy(),
            "groupe_brut": _raw_groups(data_parc).to_numpy(),
            "groupe_resolu": resolved.to_numpy(),
            "culture_representante": representative.reindex(data_parc.index).to_numpy(),
        }
    )
    frame["cultive"] = frame["groupe_resolu"] != crop_families.NON_CULTIVATED
    return frame


def _fine_variants_by_group(dataset: Dataset, config: dict[str, Any]) -> dict[str, list[str]]:
    """Observed RPG group -> the fine crops that can stand for it.

    The eight aggregate codes (AN, BA, ... -- exactly the keys of
    baseline_representative_crops) are excluded: they exist only to encode the observed
    baseline, carry no technical itinerary and no economics, and would drag any bracket to
    zero. NC is excluded for the same reason.
    """
    aggregates = set(config.get("baseline_representative_crops") or {})
    variants: dict[str, list[str]] = {}
    for crop in sorted(dataset.sets["crops"]):
        if crop in aggregates or crop == crop_families.NON_CULTIVATED:
            continue
        variants.setdefault(crop_families.base_group_for(crop), []).append(crop)
    return variants


def reproducibility_table(dataset: Dataset, config: dict[str, Any]) -> pd.DataFrame:
    """Per observed group: how much of its acreage the model could even place back.

    A plot counts as reproducible when at least one fine variant of its observed family is
    eligible on it. What is not reproducible is a deviation no objective function can avoid,
    so it is a floor under the PAD -- and it belongs to the reference, since it is a property
    of the data and the eligibility mask alone.

    Caveat kept explicit in the doc: eligibility embeds the GAMS suppressions (Eq_*_SUPP,
    Eq_VE_PLUIE banned everywhere by the ported GAMS bug), not just agronomy.
    """
    data_parc = dataset.parameters["data_parc"]
    surface = data_parc["SURF_HA"]
    mask = dataset.parameters["eligibility_mask"]
    groups = _resolved_groups(data_parc)
    variants = _fine_variants_by_group(dataset, config)

    rows = []
    for group in sorted(groups.dropna().unique()):
        if group == crop_families.NON_CULTIVATED:
            continue
        plots = groups.index[groups == group]
        candidates = variants.get(group, [])
        if candidates:
            reproducible = mask.loc[plots, candidates].any(axis=1)
        else:
            reproducible = pd.Series(False, index=plots)
        rows.append(
            {
                "groupe": group,
                "libelle": GROUP_LABELS.get(group, group),
                "variantes_fines": len(candidates),
                "observe_ha": float(surface[plots].sum()),
                "observe_parcelles": int(len(plots)),
                "reproductible_ha": float(surface[plots][reproducible].sum()),
                "reproductible_parcelles": int(reproducible.sum()),
            }
        )

    frame = pd.DataFrame(rows).set_index("groupe")
    frame["irreproductible_ha"] = frame["observe_ha"] - frame["reproductible_ha"]
    frame["part_reproductible_pct"] = 100.0 * frame["reproductible_ha"] / frame["observe_ha"]
    return frame


def representative_eligibility_table(
    dataset: Dataset, config: dict[str, Any]
) -> pd.DataFrame:
    """Per observed family: how much of its acreage the representative crop is actually
    ELIGIBLE on.

    The representative is a reporting convention, so nothing forces it to be a crop the
    model would allow on the plot -- and on this data it often is not (CS_NGT_NISM is the
    North-Grande-Terre cane system, confined to three communes, while it stands for every
    observed cane hectare). That matters twice: the reference's own economics is valued with
    a system that could not be grown there, and farm_labor_hours_max derives each farm's cap
    from those same crops, so the mismatch reaches the optimum.
    """
    data_parc = dataset.parameters["data_parc"]
    surface = data_parc["SURF_HA"]
    mask = dataset.parameters["eligibility_mask"]
    groups = _resolved_groups(data_parc)
    mapping = config.get("baseline_representative_crops") or {}

    rows = []
    for group in sorted(groups.dropna().unique()):
        if group == crop_families.NON_CULTIVATED:
            continue
        # Families with no fine variant (AG, ME, JA) stand for themselves.
        representative = mapping.get(group, group)
        plots = groups.index[groups == group]
        eligible = mask.loc[plots, representative] if representative in mask.columns else False
        rows.append(
            {
                "groupe": group,
                "representante": representative,
                "observe_ha": float(surface[plots].sum()),
                "representante_eligible_ha": float(surface[plots][eligible].sum()),
                "marge_representante_eur_ha": float(
                    dataset.parameters["margin_per_ha_cult"].get(representative, float("nan"))
                ),
            }
        )

    frame = pd.DataFrame(rows).set_index("groupe")
    frame["part_eligible_pct"] = (
        100.0 * frame["representante_eligible_ha"] / frame["observe_ha"]
    )
    return frame


def _metric_rates(dataset: Dataset) -> dict[str, pd.Series]:
    """Crop-indexed per-ha rates behind the bracketed metrics. `revenue` is bracketed on the
    combined rate, not as min(sales)+min(subsidy), which no single crop would realise."""
    parameters = dataset.parameters
    sales = parameters["sales_per_ha_cult"]
    subsidy = parameters["subsidy_per_ha_cult_annualized"]
    return {
        "production_tonnes": parameters["rdt_cult"],
        "sales": sales,
        "subsidy": subsidy,
        "revenue": sales + subsidy,
        "gross_margin": parameters["margin_per_ha_cult"],
        "labor_hours": parameters["labor_hours_per_ha_cult"],
        "azote": parameters["azote_per_ha_cult"],
        "ges": parameters["ges_per_ha_cult"],
        "ift": parameters["ift_per_ha_cult"],
    }


def _bracket_totals(
    dataset: Dataset, config: dict[str, Any]
) -> tuple[dict[str, dict[str, float]], int]:
    """Territory totals of each metric when every observed plot carries the cheapest, then
    the dearest, fine variant of its own family that it could actually carry.

    Returns (totals, fallback_plots): the number of plots where the eligibility mask leaves
    no variant of the observed family, and the bracket falls back to the family's full fine
    set (an over-estimate of the choice really available there).
    """
    data_parc = dataset.parameters["data_parc"]
    surface = data_parc["SURF_HA"]
    mask = dataset.parameters["eligibility_mask"]
    groups = _resolved_groups(data_parc)
    variants = _fine_variants_by_group(dataset, config)
    rates = _metric_rates(dataset)

    low = {metric: 0.0 for metric in _BRACKETED_METRICS}
    high = {metric: 0.0 for metric in _BRACKETED_METRICS}
    fallback_plots = 0

    for group in sorted(groups.dropna().unique()):
        if group == crop_families.NON_CULTIVATED:
            continue
        plots = groups.index[groups == group]
        candidates = variants.get(group, [])
        if not candidates:
            continue
        # .copy(): to_numpy may hand back a read-only view of the mask's block, and the
        # fallback below writes into it.
        eligible = mask.loc[plots, candidates].to_numpy(dtype=bool).copy()
        # A plot with no eligible variant keeps the whole family as its choice set: the
        # reference has to value it somehow, and pretending the choice is empty would drop
        # its hectares from the bracket entirely.
        empty = ~eligible.any(axis=1)
        fallback_plots += int(empty.sum())
        eligible[empty, :] = True
        plot_surface = surface[plots].to_numpy(dtype=float)

        for metric in _BRACKETED_METRICS:
            rate = rates[metric].reindex(candidates).to_numpy(dtype=float)
            values = np.where(eligible, rate[None, :], np.nan)
            low[metric] += float(np.nansum(np.nanmin(values, axis=1) * plot_surface))
            high[metric] += float(np.nansum(np.nanmax(values, axis=1) * plot_surface))

    return {"bas": low, "haut": high}, fallback_plots


def indicator_table(dataset: Dataset, config: dict[str, Any]) -> tuple[pd.DataFrame, int]:
    """Reference indicators: the central estimate (config's representative crops, i.e. the
    exact numbers a run reports on its input side) framed by the low/high bracket."""
    hours_per_etp = indicators.hours_per_etp_from_config(config)
    cost_per_hour = indicators.labor_cost_per_hour_from_config(config)
    representative = indicators.decode_baseline_representative_allocation(dataset, config)

    economics = indicators.compute_economic_totals(
        dataset, representative, hours_per_etp, cost_per_hour
    )
    environment = indicators.compute_environmental_totals(dataset, representative)
    bracket, fallback_plots = _bracket_totals(dataset, config)

    central = {
        "production_tonnes": economics["total_production_tonnes"],
        "sales": economics["total_revenue"] - economics["total_subsidy"],
        "subsidy": economics["total_subsidy"],
        "revenue": economics["total_revenue"],
        "gross_margin": economics["total_gross_margin"],
        "labor_hours": economics["total_etp"] * hours_per_etp,
        "azote": environment["total_azote"],
        "ges": environment["total_ges"],
        "ift": environment["total_ift"],
    }
    units = {
        "production_tonnes": "t",
        "sales": "EUR",
        "subsidy": "EUR",
        "revenue": "EUR",
        "gross_margin": "EUR",
        "labor_hours": "h",
        "azote": "kg N",
        "ges": "t CO2 (magnitude, cf. VIGILANCE)",
        "ift": "IFT.ha",
    }

    frame = pd.DataFrame(
        {
            "unite": pd.Series(units),
            "central": pd.Series(central),
            "bas": pd.Series(bracket["bas"]),
            "haut": pd.Series(bracket["haut"]),
        }
    )
    frame["amplitude_pct_du_central"] = 100.0 * (frame["haut"] - frame["bas"]) / frame["central"]
    frame.index.name = "indicateur"

    # Metrics with no bracket (they do not reduce to a per-crop per-ha rate, or the observed
    # side has no variant choice at all) still belong in the reference.
    extra = pd.DataFrame(
        {
            "unite": ["ETP", "EUR", "EUR", "ha", "m3", "t C"],
            "central": [
                economics["total_etp"],
                economics["total_labor_cost"],
                economics["total_net_revenue"],
                environment["surface_cld"],
                environment["total_water_need_m3"],
                environment["soil_carbon_balance"],
            ],
        },
        index=[
            "etp",
            "labor_cost",
            "net_revenue",
            "surface_cld",
            "water_need_m3",
            "soil_carbon_balance",
        ],
    )
    extra.index.name = "indicateur"
    return pd.concat([frame, extra]), fallback_plots


@dataclass(frozen=True)
class Reference:
    config: dict[str, Any]
    land_use: pd.DataFrame
    by_region: pd.DataFrame
    by_island: pd.DataFrame
    by_commune: pd.DataFrame
    farm_types: pd.DataFrame
    allocation: pd.DataFrame
    reproducibility: pd.DataFrame
    representative_eligibility: pd.DataFrame
    indicators: pd.DataFrame
    bracket_fallback_plots: int
    universe: dict[str, Any]


def build_reference(config: dict[str, Any]) -> Reference:
    dataset = build_dataset(config)
    data_parc = dataset.parameters["data_parc"]
    cultivated = indicators.decode_baseline_allocation(dataset)

    land_use = land_use_table(dataset)
    indicator_frame, fallback_plots = indicator_table(dataset, config)

    universe = {
        "parcelles": int(len(data_parc)),
        "exploitations": int(dataset.parameters["expl_parc"]["farm"].nunique()),
        "surface_totale_ha": float(data_parc["SURF_HA"].sum()),
        "surface_cultivee_ha": float(land_use["retenu_ha"].sum()),
        "surface_non_cultivee_ha": float(
            land_use.loc[crop_families.NON_CULTIVATED, "resolu_ha"]
        ),
        "parcelles_cultivees": int(len(cultivated)),
        "exploitations_cultivees": int(
            indicators.plot_to_farm(dataset).reindex(cultivated.index).nunique()
        ),
        "annee_economique": (config.get("data") or {}).get("year"),
        "scenario_economique": (config.get("data") or {}).get("scenario"),
        "zone_filter": config.get("zone_filter"),
        "cultures_representantes": config.get("baseline_representative_crops"),
    }

    return Reference(
        config=config,
        land_use=land_use,
        by_region=surface_by_group_and_key(
            dataset, cultivated, indicators.plot_to_region(dataset), "region"
        ),
        by_island=surface_by_group_and_key(
            dataset, cultivated, indicators.plot_to_island(dataset), "island"
        ),
        by_commune=surface_by_group_and_key(
            dataset, cultivated, data_parc["COMMUNE"], "commune"
        ),
        farm_types=farm_typology_table(dataset),
        allocation=reference_allocation(dataset, config),
        reproducibility=reproducibility_table(dataset, config),
        representative_eligibility=representative_eligibility_table(dataset, config),
        indicators=indicator_frame,
        bracket_fallback_plots=fallback_plots,
        universe=universe,
    )


def _summary(reference: Reference) -> dict[str, Any]:
    repro = reference.reproducibility
    observed = float(repro["observe_ha"].sum())
    irreproducible = float(repro["irreproductible_ha"].sum())
    return {
        "univers": reference.universe,
        "assolement_observe_ha": {
            group: float(value)
            for group, value in reference.land_use["retenu_ha"].items()
            if value > 0
        },
        "reclassement_jachere_vers_nc_ha": float(
            -reference.land_use.loc["JA", "ecart_resolution_ha"]
        ),
        "types_exploitation": {
            TYPE_EXPL_LABELS[code]: int(count)
            for code, count in reference.farm_types["exploitations"].items()
        },
        "plancher_pad_pct": 100.0 * irreproducible / observed if observed else float("nan"),
        "surface_irreproductible_ha": irreproducible,
        "parcelles_sans_variante_eligible": reference.bracket_fallback_plots,
        "representante_eligible_pct": {
            group: float(value)
            for group, value in reference.representative_eligibility[
                "part_eligible_pct"
            ].items()
        },
        "indicateurs": {
            name: {
                key: (None if pd.isna(row[key]) else float(row[key]))
                for key in ("central", "bas", "haut")
            }
            for name, row in reference.indicators.iterrows()
        },
    }


def _above_bracket(indicator_frame: pd.DataFrame) -> str:
    """Names the indicators whose central estimate sits above the high bound -- the visible
    symptom of a representative crop that is not itself eligible on the plots it stands for.
    Written from the numbers rather than by hand, so the sentence cannot go stale."""
    above = [
        f"{name} (+{100.0 * (row['central'] - row['haut']) / row['haut']:.0f} %)"
        for name, row in indicator_frame.iterrows()
        if not pd.isna(row.get("haut")) and row["central"] > row["haut"]
    ]
    return ", ".join(above) if above else "aucun indicateur dans ce run"


def _render_markdown(reference: Reference, summary: dict[str, Any]) -> str:
    universe = reference.universe
    land_use = reference.land_use
    repro = reference.reproducibility
    representative = reference.representative_eligibility

    lines = [
        "# Situation de reference -- Guadeloupe 2017",
        "",
        "Etat initial observe, reconstruit depuis l'historique RPG de `Data_Parc_Gwad_2017.txt`.",
        "C'est la situation contre laquelle chaque run est note (PAD, matrice de confusion,",
        "taux de correspondance parcellaire). Aucun solve : ce dossier ne depend d'aucun run.",
        "",
        "## 1. Univers couvert",
        "",
        f"- Parcelles : {_n(universe['parcelles'])}",
        f"- Exploitations : {_n(universe['exploitations'])}",
        f"- Surface totale : {_n(universe['surface_totale_ha'])} ha",
        f"- dont cultivee (reference PAD) : {_n(universe['surface_cultivee_ha'])} ha "
        f"sur {_n(universe['parcelles_cultivees'])} parcelles",
        f"- dont non cultivee (NC) : {_n(universe['surface_non_cultivee_ha'])} ha",
        f"- Annee / scenario economique : {universe['annee_economique']} / "
        f"{universe['scenario_economique']}",
        f"- Filtre de zone : {universe['zone_filter'] or 'aucun (territoire entier)'}",
        "",
        "**Ce n'est pas la SAU de la Guadeloupe.** L'univers est celui du jeu de donnees",
        "parcellaire disponible localement. Chopin et al. (2015) travaillent sur 5 336",
        f"exploitations, ce jeu en porte {_n(universe['exploitations'])} : les deux ne",
        "decrivent pas le meme perimetre",
        "(cf. docs/04-vigilance.md, entree de reouverture du 2026-07-27). Toute",
        "comparaison observe/simule doit donc rester **interne** a cet univers -- ce que fait",
        "le PAD, qui compare les deux cotes sur les memes parcelles.",
        "",
        "## 2. Assolement observe",
        "",
        "Deux lectures coexistent et il faut savoir laquelle on cite :",
        "",
        "- **brut** : `cult_2017` traduit directement en groupe RPG ;",
        "- **resolu** : la regle GAMS de continuite de friche (ENTREES.txt:49-57) force NC",
        "  quand `cult_2016` ET `cult_2017` sont en jachere. C'est la lecture qu'utilisent le",
        "  modele, la typologie et le PAD.",
        "",
        f"Le passage de l'une a l'autre deplace "
        f"**{_n(summary['reclassement_jachere_vers_nc_ha'])} ha** de la jachere vers le non "
        "cultive : c'est le seul ecart entre les deux lectures.",
        "",
        "| Groupe | Libelle | Brut (ha) | Resolu (ha) | Reference PAD (ha) | Part du cultive |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for group, row in land_use.iterrows():
        share = "-" if pd.isna(row["part_cultive_pct"]) else f"{row['part_cultive_pct']:.1f} %"
        lines.append(
            f"| {group} | {row['libelle']} | {_n(row['brut_ha'])} | {_n(row['resolu_ha'])} | "
            f"{_n(row['retenu_ha'])} | {share} |"
        )
    lines += [
        f"| **TOTAL** | | {_n(land_use['brut_ha'].sum())} | {_n(land_use['resolu_ha'].sum())} | "
        f"{_n(land_use['retenu_ha'].sum())} | 100 % |",
        "",
        "Declinaisons : `csv/reference_surface_by_region.csv`, `_by_island.csv`,",
        "`_by_commune.csv`. Reference parcelle par parcelle : `csv/reference_allocation.csv`.",
        "",
        "## 3. Typologie des exploitations observee",
        "",
        "Marge-ligne de toute matrice de confusion, et source du coefficient d'aversion au",
        "risque (AVERS) de chaque ferme dans l'objectif de Markowitz : c'est un element de la",
        "reference, pas un resultat.",
        "",
        "| Type | Libelle | Exploitations | Part | Surface (ha) | AVERS |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for code, row in reference.farm_types.iterrows():
        avers = (
            f"{row['avers_min']:.2f}"
            if row["avers_min"] == row["avers_max"]
            else f"{row['avers_min']:.2f}-{row['avers_max']:.2f}"
        )
        lines.append(
            f"| {code} | {row['libelle']} | {_n(row['exploitations'])} | "
            f"{row['part_exploitations_pct']:.1f} % | {_n(row['surface_ha'])} | {avers} |"
        )

    lines += [
        "",
        "## 4. Ce que la reference ne peut pas dire",
        "",
        "### 4.1 Aucune culture fine observee",
        "",
        "Les 12 groupes RPG disent « canne », jamais quel systeme technique. Le GAMS avait la",
        "meme limite (`Matrice_Parc_Cult`). Tout indicateur economique ou environnemental de",
        "la reference passe donc par une **culture representante** par famille",
        "(`config.yaml: baseline_representative_crops`) -- une hypothese, pas une observation.",
        "",
        "**Premier constat, quantifie ici pour la premiere fois : la representante est souvent",
        "une culture que le modele lui-meme interdirait sur la parcelle qu'elle represente.**",
        "`CS_NGT_NISM` est le systeme cannier du Nord Grande-Terre, cantonne a trois communes,",
        "et il vaut pourtant tous les hectares de canne du territoire ; `MA_ROTA` exige",
        "l'irrigation et vaut tout le maraichage.",
        "",
        "| Groupe | Representante | Observe (ha) | Representante eligible (ha) | Part | Marge (EUR/ha) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for group, row in representative.iterrows():
        lines.append(
            f"| {group} | `{row['representante']}` | {_n(row['observe_ha'])} | "
            f"{_n(row['representante_eligible_ha'])} | {row['part_eligible_pct']:.0f} % | "
            f"{_n(row['marge_representante_eur_ha'])} |"
        )

    lines += [
        "",
        "**Consequence a ne pas perdre de vue** : cette hypothese ne reste pas dans le",
        "reporting. `farm_labor_hours_max` (Eq_MO_MAX_Expl) plafonne chaque exploitation a la",
        "main d'oeuvre de son assolement observe, calculee via ces memes representantes :",
        "changer une representante change le plafond, donc l'optimum. Cf. docs/04-vigilance.md et",
        "l'entree « cultures representantes conscientes de la region » de TODO.md, que ce",
        "tableau chiffre.",
        "",
        "Les indicateurs de la reference sont donc donnes avec une fourchette. L'estimation",
        "**centrale** est celle des representantes du `config.yaml` -- exactement les chiffres",
        "que reporte le cote « entree » d'un run, pour que les deux racontent la meme histoire.",
        "Les bornes **bas** et **haut** rejouent chaque parcelle avec la variante la moins,",
        "puis la plus intense **parmi celles qui y sont reellement eligibles**.",
        "",
        "Rien ne garantit alors que le central tombe dans la fourchette -- la representante",
        "n'appartient pas toujours a l'ensemble des variantes eligibles. La ou il en sort par",
        "le haut, la reference est valorisee par un systeme technique que la parcelle ne",
        f"pourrait pas porter : {_above_bracket(reference.indicators)}.",
        "",
        "| Indicateur | Unite | Bas | Central | Haut | Amplitude |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, row in reference.indicators.iterrows():
        amplitude = (
            "-"
            if pd.isna(row.get("amplitude_pct_du_central"))
            else f"{row['amplitude_pct_du_central']:.0f} %"
        )
        lines.append(
            f"| {name} | {row['unite']} | {_n(row.get('bas'))} | {_n(row['central'])} | "
            f"{_n(row.get('haut'))} | {amplitude} |"
        )

    lines += [
        "",
        f"La fourchette retombe sur la famille entiere pour "
        f"{reference.bracket_fallback_plots} parcelle(s) sans aucune variante eligible.",
        "",
        "### 4.2 Une partie de l'observe est irreproductible par construction",
        "",
        "Une parcelle n'est reproductible que si au moins une variante fine de sa famille",
        "observee y est eligible. Ce qui ne l'est pas est un ecart qu'aucun objectif ne peut",
        "eviter : c'est un **plancher sous le PAD**, propriete des donnees et du masque",
        "d'eligibilite, pas du run.",
        "",
        "| Groupe | Observe (ha) | Reproductible (ha) | Irreproductible (ha) | Part reproductible |",
        "|---|---:|---:|---:|---:|",
    ]
    for group, row in repro.iterrows():
        lines.append(
            f"| {group} | {_n(row['observe_ha'])} | {_n(row['reproductible_ha'])} | "
            f"{_n(row['irreproductible_ha'])} | {row['part_reproductible_pct']:.0f} % |"
        )
    lines += [
        f"| **TOTAL** | {_n(repro['observe_ha'].sum())} | "
        f"{_n(repro['reproductible_ha'].sum())} | {_n(repro['irreproductible_ha'].sum())} | "
        f"{100.0 * repro['reproductible_ha'].sum() / repro['observe_ha'].sum():.0f} % |",
        "",
        f"Plancher de PAD induit : **{summary['plancher_pad_pct']:.1f} %** "
        f"({_n(summary['surface_irreproductible_ha'])} ha sur "
        f"{_n(repro['observe_ha'].sum())} ha), et jusqu'au double si l'on compte aussi",
        "l'exces cree ailleurs par ces hectares deplaces. C'est faible :",
        "**l'ecart observe/simule ne s'explique pas par l'eligibilite.**",
        "",
        "L'eligibilite embarque aussi les suppressions GAMS (`Eq_*_SUPP`, et `Eq_VE_PLUIE`",
        "interdite partout par le bug GAMS porte fidelement) : les vergers et les agrumes sont",
        "donc irreproductibles pour une raison de portage, pas d'agronomie.",
        "",
        "## 5. Fichiers",
        "",
        "| Fichier | Contenu |",
        "|---|---|",
        "| `csv/reference_land_use.csv` | Assolement observe, lectures brute et resolue |",
        "| `csv/reference_allocation.csv` | Reference parcelle par parcelle (la table pivot) |",
        "| `csv/reference_surface_by_region.csv` | Surface cultivee par region x groupe |",
        "| `csv/reference_surface_by_island.csv` | Idem par ile |",
        "| `csv/reference_surface_by_commune.csv` | Idem par commune |",
        "| `csv/reference_farm_types.csv` | Typologie observee et AVERS |",
        "| `csv/reference_indicators.csv` | Indicateurs, central et fourchette |",
        "| `csv/reference_reproducibility.csv` | Plancher de PAD par groupe |",
        "| `csv/reference_representative_eligibility.csv` | Eligibilite des representantes |",
        "| `reference.json` | Le tout, lisible par un script |",
        "",
        "Regenerer : `python scripts/build_reference_state.py`. Deterministe (aucun solve).",
        "",
    ]
    return "\n".join(lines)


def write_reference(reference: Reference, output_dir: Path) -> dict[str, Any]:
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)

    reference.land_use.to_csv(csv_dir / "reference_land_use.csv")
    reference.allocation.to_csv(csv_dir / "reference_allocation.csv", index=False)
    reference.by_region.to_csv(csv_dir / "reference_surface_by_region.csv")
    reference.by_island.to_csv(csv_dir / "reference_surface_by_island.csv")
    reference.by_commune.to_csv(csv_dir / "reference_surface_by_commune.csv")
    reference.farm_types.to_csv(csv_dir / "reference_farm_types.csv")
    reference.indicators.to_csv(csv_dir / "reference_indicators.csv")
    reference.reproducibility.to_csv(csv_dir / "reference_reproducibility.csv")
    reference.representative_eligibility.to_csv(
        csv_dir / "reference_representative_eligibility.csv"
    )

    summary = _summary(reference)
    (output_dir / "reference.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "REFERENCE.md").write_text(
        _render_markdown(reference, summary), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        type=Path,
        default=OUTPUTS_ROOT / DEFAULT_DIR_NAME,
        help=f"Destination folder (default outputs/{DEFAULT_DIR_NAME}).",
    )
    args = parser.parse_args(argv)

    config = load_config(CONFIG_PATH)
    reference = build_reference(config)
    summary = write_reference(reference, args.dir)

    universe = summary["univers"]
    print(f"\n=== Situation de reference 2017 -> {args.dir} ===")
    print(
        f"  Univers                     : {universe['parcelles']} parcelles, "
        f"{universe['exploitations']} exploitations, "
        f"{universe['surface_totale_ha']:,.0f} ha"
    )
    print(
        f"  Surface cultivee (ref. PAD) : {universe['surface_cultivee_ha']:,.0f} ha "
        f"({universe['parcelles_cultivees']} parcelles)"
    )
    print(
        f"  Jachere reclassee en NC     : "
        f"{summary['reclassement_jachere_vers_nc_ha']:,.0f} ha"
    )
    print(
        f"  Plancher de PAD (eligibilite): {summary['plancher_pad_pct']:.1f} % "
        f"({summary['surface_irreproductible_ha']:,.0f} ha irreproductibles)"
    )
    print("\n  Assolement observe (ha) :")
    for group, value in sorted(
        summary["assolement_observe_ha"].items(), key=lambda item: -item[1]
    ):
        print(f"    {group:<3} {GROUP_LABELS.get(group, ''):<22} {value:>9,.0f}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
