from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass
class ModelInputs:
    """Everything the constraint and objective builders may read, in case-study-neutral
    terms. Only the first three are always needed; a builder given nothing for an optional
    field simply finds nothing to constrain.
    """

    plot_surface_ha: Mapping[str, float]
    crop_margin_per_ha: Mapping[str, float]
    eligible_pairs: Sequence[tuple[str, str]]
    farm_plots: Mapping[str, Sequence[str]] = field(default_factory=dict)
    farm_surface_ha: Mapping[str, float] = field(default_factory=dict)
    # Surface of the subset of a farm's plots flagged as subject to a land-tenure scheme,
    # for rules that apply a quota to that subset only rather than the whole farm.
    farm_restricted_surface_ha: Mapping[str, float] = field(default_factory=dict)
    crop_yield_per_ha: Mapping[str, float] = field(default_factory=dict)
    crop_variance_per_ha: Mapping[str, float] = field(default_factory=dict)
    farm_risk_aversion: Mapping[str, float] = field(default_factory=dict)
    # Labour a crop demands per hectare-year, and the labour a farm is assumed to have.
    # The capacity is a *stock* the case study derives from its own observed baseline; core
    # only reads it. A farm absent from the mapping is simply not capped.
    crop_labor_hours_per_ha: Mapping[str, float] = field(default_factory=dict)
    farm_labor_capacity_hours: Mapping[str, float] = field(default_factory=dict)
    # Per-hectare rate of any indicator the case study chooses to expose, keyed by indicator
    # name then crop: {"azote": {"CS_BT_NISM": 118.0, ...}, "ift": {...}}. This is what makes
    # a regulatory ceiling (nitrogen, pesticide index, GHG, water) or a public-spending
    # envelope expressible from config without a new builder per indicator -- the units are
    # the case study's business, core only multiplies by hectares. A crop missing from a rate
    # mapping contributes 0.
    crop_indicator_rates: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    # Groupings a bound may be applied within, keyed by grouping name then plot:
    # {"islands": {"P1": 1, ...}, "watersheds": {...}, "farms": {...}}. Lets the same
    # indicator bound hold per island / per catchment / per farm rather than territory-wide.
    plot_zones: Mapping[str, Mapping[str, object]] = field(default_factory=dict)
    # Per-plot multipliers a bound may weight its hectares by, keyed by weight name then
    # plot: {"irrigable": {"P1": 1.0, "P2": 0.0, ...}}. Indicator rates are per crop, so
    # without this a bound cannot express a quantity that depends on the plot as well --
    # water drawn from the network, which only irrigable plots take, being the case that
    # forces it. A plot absent from a named weight mapping counts as 0.
    plot_weights: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
    # Crop -> aggregate group it belongs to, and each plot's group in the OBSERVED baseline.
    # Together they say whether assigning a crop to a plot keeps that plot in its historical
    # use, which is what an inertia / transition-cost rule needs. Plots absent from
    # plot_baseline_group have no historical use to keep.
    crop_group: Mapping[str, str] = field(default_factory=dict)
    plot_baseline_group: Mapping[str, str] = field(default_factory=dict)
    # Production a farm is allowed, in the crop's own output unit, keyed by reference name
    # then farm: {"BA": {"E1": 1200.0, ...}}. Like farm_labor_capacity_hours this is a stock
    # the case study derives from its own observed baseline -- core only reads it -- but
    # indexed by reference so several independent quotas (one per market) can coexist.
    # A farm absent from a reference is left unconstrained, never defaulted to zero.
    farm_production_capacity: Mapping[str, Mapping[str, float]] = field(default_factory=dict)
