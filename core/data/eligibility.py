import pandas as pd


def compute_eligibility_mask(
    plot_attributes: pd.DataFrame,
    crop_bounds: pd.DataFrame,
    attribute_bounds: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    mask = pd.DataFrame(True, index=plot_attributes.index, columns=crop_bounds.index)
    for attribute, (min_col, max_col) in attribute_bounds.items():
        values = plot_attributes[attribute].to_numpy()[:, None]
        mins = crop_bounds[min_col].to_numpy()[None, :]
        maxs = crop_bounds[max_col].to_numpy()[None, :]
        within_bounds = (values >= mins) & (values <= maxs)
        mask &= pd.DataFrame(
            within_bounds, index=plot_attributes.index, columns=crop_bounds.index
        )
    return mask


def eligible_pairs_from_mask(mask: pd.DataFrame) -> list[tuple[str, str]]:
    stacked = mask.stack()
    return list(stacked[stacked].index)
