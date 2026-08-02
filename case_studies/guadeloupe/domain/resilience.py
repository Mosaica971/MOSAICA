"""Exposure of a fixed allocation to climatic and economic shocks.

These indicators measure what is *at stake* if a shock lands after the cropping decisions
are locked in. They do NOT re-optimize, so they are not a measure of adaptive capacity --
see the design spec and docs/04-vigilance.md. The `price_multipliers` / `yield_multipliers` config
levers do the other thing: they shock the inputs *before* the solve, letting the optimizer
adapt.

Var_Rdt_Cult is a *fractional margin loss*, not a variance and not a coefficient of
variation. GAMS uses it that way in both places it appears: OPTIMISATION.txt:70
(`MB_Ha_Cult_Pond = MB_Ha_Cult - MB_Ha_Cult * Var_Rdt_Cult`) and MODELE.txt:427 (the
Markovitz penalty). The loss is therefore linear in area -- no squaring, no covariance.
"""

import pandas as pd

# Default relative price shock applied to prix_cult. Overridable via
# config.yaml resilience.price_shock_delta.
DEFAULT_PRICE_SHOCK_DELTA = 0.20

# Annualization factor shared with economics.py: per-cycle figures are scaled by
# 12 / Duree_Cycle_Cult (months) to get a per-year figure.
_MONTHS_PER_YEAR = 12


def compute_climate_margin_at_risk_per_ha_cult(
    margin_per_ha_cult: pd.Series, var_rdt_cult: pd.Series
) -> pd.Series:
    """Gross margin at risk (EUR/ha/year) if a bad year hits: margin times the crop's
    fractional yield loss."""
    return margin_per_ha_cult * var_rdt_cult.reindex(margin_per_ha_cult.index)


def compute_price_shock_loss_per_ha_cult(
    rdt_cult: pd.Series,
    prix_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    delta: float,
) -> pd.Series:
    """Margin lost (EUR/ha/year) under a relative price shock `delta` on prix_cult.

    Closed form: subsidies are fixed amounts (not indexed on market prices), variable costs
    scale with yield rather than price, and the bagasse by-product price is left alone -- so
    the whole loss is `delta * annualized market sales`, with no need to re-run economics.py.
    """
    annual_market_sales = rdt_cult * prix_cult / duree_cycle_cult * _MONTHS_PER_YEAR
    return delta * annual_market_sales


def compute_revenue_concentration_hhi(revenue_by_crop: pd.Series) -> float:
    """Herfindahl index of revenue concentration, in [0, 1]. 1 = a single crop earns
    everything; 1/n = n crops earn equal shares. Higher means more fragile to anything
    hitting one crop.

    Computed on revenue rather than gross margin on purpose: margin can be negative for a
    crop (notably on the baseline side, where representative crops are not picked for
    profitability), and shares that do not sum to 1 make the index meaningless. Revenue
    (sales + subsidy) is always non-negative.
    """
    total = float(revenue_by_crop.sum())
    if total <= 0:
        return 0.0
    shares = revenue_by_crop / total
    return float((shares**2).sum())
