import pandas as pd


def compute_variable_cost_per_ha_cult(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    cout_recolte_cult: pd.Series,
    cout_transp_cult: pd.Series,
    rdt_cult: pd.Series,
) -> pd.Series:
    """CV_Ha_Cult: variable cost per ha (OPTIMISATION.GMS lines 11-19).

    Each OTK (technical operation) costs dose*price per application. Amortized
    operations (AMORTI=1, e.g. plantation) are spread over the plantation
    lifetime (Duree_Plant_Cult); one-off operations (AMORTI=0) are not.
    """
    cost_per_application = data_otk["DOSE"] * data_otk["PRIX_UNIT"]
    otk_cost = matrice_otk_cult.multiply(cost_per_application, axis=0)

    amortized = data_otk["AMORTI"] == 1
    otk_cost_amortized = otk_cost.mul(amortized.astype(float), axis=0).div(
        duree_plant_cult, axis=1
    )
    otk_cost_upfront = otk_cost.mul((~amortized).astype(float), axis=0)

    cost_from_otk = (otk_cost_upfront + otk_cost_amortized).sum(axis=0) / duree_cycle_cult * 12

    return cost_from_otk + (cout_recolte_cult + cout_transp_cult) * rdt_cult


def compute_labor_hours_per_ha_cult(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """MO_Ha_Cult: labor hours per ha per year (ENTREES.txt:463-466).

    Same OTK structure as compute_variable_cost_per_ha_cult, but each technical
    operation is weighted by its labor requirement (DOSE*MO_EXPL, in hours) instead
    of its monetary cost (DOSE*PRIX_UNIT). Amortized operations (AMORTI=1, e.g.
    plantation) are spread over the plantation lifetime; one-off operations are not.
    Unlike cost, there is no harvest/transport term -- labor is entirely in the OTK.
    """
    labor_per_application = data_otk["DOSE"] * data_otk["MO_EXPL"]
    otk_labor = matrice_otk_cult.multiply(labor_per_application, axis=0)

    amortized = data_otk["AMORTI"] == 1
    otk_labor_amortized = otk_labor.mul(amortized.astype(float), axis=0).div(
        duree_plant_cult, axis=1
    )
    otk_labor_upfront = otk_labor.mul((~amortized).astype(float), axis=0)

    return (otk_labor_upfront + otk_labor_amortized).sum(axis=0) / duree_cycle_cult * 12


def compute_subsidy_per_ha_cult(
    posei_surf_cult: pd.Series,
    posei_q_cult: pd.Series,
    aide_indus_cult: pd.Series,
    aide_replant_cult: pd.Series,
    aide_transp_cult: pd.Series,
    aide_garantie_prix_cult: pd.Series,
    mae_recolte_vert_cult: pd.Series,
    mae_jachere_sol_nu_cult: pd.Series,
    mae_compost_cult: pd.Series,
    mb_add_cult: pd.Series,
    rdt_cult: pd.Series,
    duree_cycle_cult: pd.Series,
    duree_plant_cult: pd.Series,
) -> pd.Series:
    """SUB_TOT_Ha_Cult: total subsidies per ha (OPTIMISATION.GMS lines 21-34).

    Sums POSEI (EU aid), national, and PDRG (agri-environmental, MAE) subsidy
    schemes, plus a flat additional-margin adjustment (MB_ADD_Cult).
    """
    posei = (
        posei_surf_cult
        + (posei_q_cult + aide_indus_cult) * rdt_cult / duree_cycle_cult * 12
        + aide_replant_cult / duree_plant_cult
    )
    national = (aide_transp_cult + aide_garantie_prix_cult) * rdt_cult / duree_cycle_cult * 12
    pdrg = mae_recolte_vert_cult + mae_jachere_sol_nu_cult + mae_compost_cult

    return posei + national + pdrg + mb_add_cult


def compute_sales_per_ha_cult(
    rdt_cult: pd.Series,
    prix_cult: pd.Series,
    bagasse_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """Sales-only component of PB_Ha_Cult, annualized the same way (excludes subsidy)."""
    return rdt_cult * (prix_cult + bagasse_cult) / duree_cycle_cult * 12


def compute_gross_product_per_ha_cult(
    rdt_cult: pd.Series,
    prix_cult: pd.Series,
    bagasse_cult: pd.Series,
    subsidy_per_ha_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.Series:
    """PB_Ha_Cult: gross product per ha, annualized (OPTIMISATION.GMS lines 36-38)."""
    sales = compute_sales_per_ha_cult(rdt_cult, prix_cult, bagasse_cult, duree_cycle_cult)
    return sales + subsidy_per_ha_cult / duree_cycle_cult * 12


def compute_gross_margin_per_ha_cult(
    gross_product_per_ha_cult: pd.Series,
    variable_cost_per_ha_cult: pd.Series,
) -> pd.Series:
    """MB_Ha_Cult: gross margin per ha (OPTIMISATION.GMS lines 40-42)."""
    return gross_product_per_ha_cult - variable_cost_per_ha_cult
