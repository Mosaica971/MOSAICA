"""Human-readable English labels for the fine crop codes in CULT_2017.set.

Translated from context/gams/DESCRIPTION_SETS.txt (the GAMS source of truth, in French).
Figures and exports use these instead of raw codes. The 24 MA_<mulch>_* market-gardening
subtypes are not individually described in the GAMS source: mulch (BAG = bagasse, BRF =
ramial chipped wood, PAI = straw) and irrigation (I/NI) are decoded; the middle fertilisation
token (BIO/VEG/FER/NON) is kept literal because its meaning is undocumented -- and it carries
no data either (see crop_groups.yaml, "Karusmart"). label_for() falls back to the raw code
for anything unmapped.
"""

_MULCH = {"BAG": "bagasse", "BRF": "ramial wood chips", "PAI": "straw"}
_WATER = {"I": "irrigated", "NI": "rain-fed"}

CROP_LABELS: dict[str, str] = {
    "AG": "Citrus",
    "AN": "Pineapple",
    "AN_NU": "Pineapple: system without plastic mulch",
    "AN_PA": "Pineapple: system with plastic mulch",
    "BA": "Dessert banana",
    "BA_INT": "Banana: intensive lowland system",
    "BA_IRR": "Banana: irrigated system",
    "BA_PER": "Banana: extensive upland system",
    "BA_SINT": "Banana: intensive upland system",
    "BC": "Plantain",
    "BC_BT": "Plantain, Basse-Terre",
    "BC_GTMG": "Plantain, Grande-Terre & Marie-Galante",
    "CF_NBT_NISM": "Fibre cane: North Basse-Terre, rain-fed, semi-mechanised harvest",
    "CF_NBT_NIM": "Fibre cane: North Basse-Terre, rain-fed, mechanised harvest",
    "CF_SBT_NISM": "Fibre cane: South Basse-Terre, rain-fed, semi-mechanised harvest",
    # The French source label read "Nord Basse-Terre" here, a copy slip: the code and the
    # GAMS ban Eq_CF_SBT (MODELE.txt:75) both say South Basse-Terre.
    "CF_SBT_NIM": "Fibre cane: South Basse-Terre, rain-fed, mechanised harvest",
    "CF_NGT_NISM": "Fibre cane: North Grande-Terre, rain-fed, semi-mechanised harvest",
    "CF_NGT_NIM": "Fibre cane: North Grande-Terre, rain-fed, mechanised harvest",
    "CF_CGT_NISM": "Fibre cane: Central Grande-Terre, rain-fed, semi-mechanised harvest",
    "CF_CGT_NIM": "Fibre cane: Central Grande-Terre, rain-fed, mechanised harvest",
    "CF_EGT_NISM": "Fibre cane: East Grande-Terre, rain-fed, semi-mechanised harvest",
    "CF_EGT_NIM": "Fibre cane: East Grande-Terre, rain-fed, mechanised harvest",
    "CS": "Sugarcane",
    "CS_BT_NISM": "Sugarcane: Basse-Terre, rain-fed, semi-mechanised harvest",
    "CS_BT_NIM": "Sugarcane: Basse-Terre, rain-fed, mechanised harvest",
    "CS_BT_IM": "Sugarcane: Basse-Terre, irrigated, mechanised harvest",
    "CS_SBT_NISM": "Sugarcane: South-East Basse-Terre, rain-fed, semi-mechanised harvest",
    "CS_SBT_NIM": "Sugarcane: South-East Basse-Terre, rain-fed, mechanised harvest",
    "CS_SBT_IM": "Sugarcane: South-East Basse-Terre, irrigated, mechanised harvest",
    "CS_NGT_NISM": "Sugarcane: North Grande-Terre, rain-fed, semi-mechanised harvest",
    "CS_NGT_NIM": "Sugarcane: North Grande-Terre, rain-fed, mechanised harvest",
    "CS_NGT_IM": "Sugarcane: North Grande-Terre, irrigated, mechanised harvest",
    "CS_CGT_NISM": "Sugarcane: Central Grande-Terre, rain-fed, semi-mechanised harvest",
    "CS_CGT_NIM": "Sugarcane: Central Grande-Terre, rain-fed, mechanised harvest",
    "CS_CGT_IM": "Sugarcane: Central Grande-Terre, irrigated, mechanised harvest",
    "CS_EGT_NISM": "Sugarcane: East Grande-Terre, rain-fed, semi-mechanised harvest",
    "CS_EGT_NIM": "Sugarcane: East Grande-Terre, rain-fed, mechanised harvest",
    "CS_EGT_IM": "Sugarcane: East Grande-Terre, irrigated, mechanised harvest",
    "CS_MG_NISM": "Sugarcane: Marie-Galante, rain-fed, semi-mechanised harvest",
    "CS_MG_NIM": "Sugarcane: Marie-Galante, rain-fed, mechanised harvest",
    "CS_MG_IM": "Sugarcane: Marie-Galante, irrigated, mechanised harvest",
    "IG": "Yam and tropical tubers",
    "IG_PLA": "Yam, flat-grown",
    "IG_TUT": "Yam, staked",
    "JA": "Fallow",
    "MA": "Open-field market gardening, excluding tropical tubers",
    "MA_TO_CHOU_JA": "Open-field market gardening (tomato/cabbage/fallow rotation)",
    # "CO" is not described in the GAMS source; kept literal rather than guessed.
    "MA_TO_CO_JA": "Open-field market gardening (TO/CO/JA rotation)",
    "MA_PLBIO": "Organic multi-species market gardening",
    "MA_MOBIO": "Organic single-species market gardening",
    "MA_ROTA": "Market gardening in rotation",
    "ME": "Melon",
    "NC": "Not cultivated",
    "PN": "Grassland & savannah",
    "PN_PIQ": "Natural grassland with tethered livestock",
    "PN_TOUR": "Natural grassland with rotational grazing",
    "TH": "Tomato",
    "VE": "Orchards excluding citrus",
    "VE_BTGT": "Orchards: Basse-Terre & Grande-Terre",
    "VE_PLUIE": "Orchards: very rainy areas",
}
CROP_LABELS.update(
    {
        f"MA_{mulch}_{fert}_{water}": (
            f"Open-field market gardening ({_MULCH[mulch]}, {fert}, {_WATER[water]})"
        )
        for mulch in _MULCH
        for fert in ("BIO", "VEG", "FER", "NON")
        for water in _WATER
    }
)


def label_for(code: str) -> str:
    """Explicit crop name for a CULT_2017 code, or the code itself if unmapped."""
    return CROP_LABELS.get(code, code)
