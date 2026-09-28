"""The status board: what the model implements, at which resolution, and on which choices.

Four tables, built by scripts/build_status_board.py (-> docs/status/STATUS.md) and shown by
the dashboard's Status page:

1. indicators x aggregation levels, from status/indicator_catalog.yaml;
2. constraints and eligibility rules x crops, derived from config.yaml itself;
3. parameters with several plausible values, from status/parameter_choices.yaml, each checked
   against the value config.yaml actually holds;
4. the implementation roadmap, from docs/status/roadmap.yaml.

Tables 2 and 3 are generated or checked against the code, so they cannot silently drift;
tables 1 and 4 are declarations, guarded by tests/test_status_board.py. Pure: no Streamlit,
no solve. Only the optional eligibility counts need the data (build_dataset, ~7 s).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from case_studies.guadeloupe.domain.crop_families import base_group_for

CASE_STUDY_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = CASE_STUDY_DIR.parents[1]
INDICATOR_CATALOG = CASE_STUDY_DIR / "status" / "indicator_catalog.yaml"
PARAMETER_CHOICES = CASE_STUDY_DIR / "status" / "parameter_choices.yaml"
ROADMAP = REPO_ROOT / "docs" / "status" / "roadmap.yaml"
GAMS_DIR = REPO_ROOT / "context" / "gams"

ROADMAP_STATUSES = (
    "done", "in_progress", "todo", "to_update", "proposal", "blocked", "abandoned",
)
INDICATOR_CLASSES = ("additive", "ratio", "non_additive", "territorial", "observed")

# Cell values of the indicator x level table.
REPORTED = "reported"
COMPUTABLE = "computable"
NEEDS_DEFINITION = "needs definition"
NOT_APPLICABLE = "n/a"


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


# --------------------------------------------------------------------------- 1. indicators
def load_indicator_catalog(path: Path = INDICATOR_CATALOG) -> tuple[list[str], pd.DataFrame]:
    """(levels, one row per indicator) from the catalogue."""
    document = _load_yaml(path)
    frame = pd.DataFrame(document.get("indicators") or [])
    return list(document.get("levels") or []), frame


def _cell(indicator_class: str, level: str, reported: list[str]) -> str:
    if level in reported:
        return REPORTED
    if indicator_class in ("additive", "ratio"):
        return COMPUTABLE
    if indicator_class == "non_additive":
        return NEEDS_DEFINITION
    if indicator_class == "observed":
        # The observation exists at the 12 RPG groups only, never at a fine crop.
        return NOT_APPLICABLE if level == "crop" else COMPUTABLE
    return NOT_APPLICABLE  # territorial: its denominator exists for the territory only


def indicator_level_matrix(levels: list[str], catalog: pd.DataFrame) -> pd.DataFrame:
    """Indicator x level: reported today, computable from the data, or not meaningful.

    "computable" is a claim about the data, not about the code: an additive indicator can be
    summed over any plot -> zone mapping, which exists for every level listed.
    """
    rows = {}
    for _, entry in catalog.iterrows():
        reported = list(entry.get("reported") or [])
        rows[entry["key"]] = {level: _cell(entry["class"], level, reported) for level in levels}
    matrix = pd.DataFrame.from_dict(rows, orient="index")[levels]
    matrix.insert(0, "class", catalog.set_index("key")["class"])
    matrix.insert(0, "family", catalog.set_index("key")["family"])
    matrix.insert(0, "label", catalog.set_index("key")["label"])
    return matrix


# --------------------------------------------------------------------- 2. constraints x crops
_SECTIONS = ("constraints", "eligibility_criteria", "categorical_rules")

# Labels whose GAMS equation name does not follow Eq_<LABEL> (after _farm -> _Expl).
_GAMS_EQUATION_OVERRIDES: dict[str, str] = {
    "labor_max_farm": "Eq_MO_MAX_Expl",
    "ba_quota_farm": "Eq_BA_QUOTA_Expl",
    "fallow": "Eq_FRICHE",
    "ig_tut_chlordecone": "Eq_IG_CLD",
    "pn_piq_cld": "Eq_PN_PIQ_CLD",
    "cs_irrig_ban": "Eq_CS_IRR",
    "nocult_nc_1": "Eq_NOCULT_NC",
    "nocult_nc_2": "Eq_NOCULT_NC",
}


def gams_equations(gams_dir: Path = GAMS_DIR) -> dict[str, str]:
    """{upper-cased name: name as written} of every `Eq_*` identifier in the GAMS sources."""
    names: dict[str, str] = {}
    if not gams_dir.is_dir():
        return names
    for path in gams_dir.glob("*.txt"):
        text = path.read_text(encoding="latin-1")
        for match in re.finditer(r"\bEq_[A-Za-z0-9_]+", text):
            names.setdefault(match.group(0).upper(), match.group(0))
    return names


def gams_equation_for(label: str | None, known: dict[str, str]) -> str | None:
    """The GAMS equation a config label ports, when it can be found in the sources."""
    if not label:
        return None
    candidates = [_GAMS_EQUATION_OVERRIDES.get(label)] if label in _GAMS_EQUATION_OVERRIDES else []
    stem = label.upper()
    candidates += [f"Eq_{stem}", f"Eq_{stem.replace('_FARM', '_EXPL')}"]
    for candidate in candidates:
        if candidate and candidate.upper() in known:
            return known[candidate.upper()]
    return None


_EQUATION_TOKEN = re.compile(r"\bEq_[A-Za-z0-9_]+")


def gams_equations_from_comments(config_text: str) -> dict[tuple[str, int], list[str]]:
    """{(section, position): Eq_* names} read from the comments of config.yaml.

    The GAMS geographic bans carry no label, but each is preceded (or followed on the same
    line) by a comment naming its equation. The inline comment wins; otherwise the nearest
    comment line above the entry that names one. Only list entries at the section's own
    indentation (`  - name:`) count.
    """
    found: dict[tuple[str, int], list[str]] = {}
    section, position, block = None, -1, []
    for line in config_text.splitlines():
        top = re.match(r"^([A-Za-z_]+):", line)
        if top:
            section, position, block = top.group(1), -1, []
            continue
        if section not in _SECTIONS:
            continue
        stripped = line.strip()
        if line.startswith("  - name:"):
            position += 1
            inline = line.split("#", 1)[1] if "#" in line else ""
            tokens = _EQUATION_TOKEN.findall(inline)
            if not tokens:
                for comment in reversed(block):
                    tokens = _EQUATION_TOKEN.findall(comment)
                    if tokens:
                        break
            if tokens:
                found[(section, position)] = tokens
            block = []
        elif stripped.startswith("#"):
            block.append(stripped)
        elif stripped:
            block = []
    return found


def _crops_of(args: dict[str, Any]) -> list[str] | str:
    """Crops an entry touches, read from its arguments; "*" when it applies to every crop."""
    crops: list[str] = []
    for key in ("crops", "numerator_crops", "denominator_crops"):
        value = args.get(key)
        if value == "*":
            return "*"
        if isinstance(value, list):
            crops += [str(c) for c in value]
    for group in args.get("groups") or []:
        crops += [str(c) for c in (group.get("crops") or [])]
    return list(dict.fromkeys(crops)) or "*"


def _role(section: str, name: str, args: dict[str, Any]) -> str:
    if section == "eligibility_criteria":
        return "eligibility bound"
    if section == "categorical_rules":
        return "ban"
    sense = args.get("sense")
    if sense == "le":
        return "ceiling"
    if sense == "ge":
        return "floor"
    if name.endswith("_max"):
        return "ceiling"
    if name.endswith(("_min", "_min_share")) or "minimum" in name:
        return "floor"
    return "structure"


def constraint_table(
    config: dict[str, Any], gams_dir: Path = GAMS_DIR, config_text: str | None = None
) -> pd.DataFrame:
    """One row per constraint, eligibility criterion and categorical rule of the config,
    enabled or not: its role, the crops it touches and the GAMS equation it ports.

    The equation comes from the label when it follows the GAMS name, else from the config's
    own comments (`config_text`); either way it is shown only if it exists in the sources.
    """
    known = gams_equations(gams_dir)
    commented = gams_equations_from_comments(config_text) if config_text else {}
    rows = []
    for section in _SECTIONS:
        for position, entry in enumerate(config.get(section) or []):
            args = entry.get("args") or {}
            label = args.get("label") or (entry["name"] if section == "eligibility_criteria" else None)
            crops = _crops_of(args) if section != "eligibility_criteria" else "*"
            if entry["name"] in ("at_most_one_crop_per_plot", "farm_labor_hours_max",
                                 "baseline_inertia_min"):
                crops = "*"
            equation = gams_equation_for(label, known)
            if equation is None:
                equation = next(
                    (known[t.upper()] for t in commented.get((section, position), [])
                     if t.upper() in known),
                    None,
                )
            rows.append(
                {
                    "section": section,
                    "position": position,
                    "name": entry["name"],
                    "label": label or "",
                    "enabled": bool(entry.get("enable", False)),
                    "role": _role(section, entry["name"], args),
                    "gams_equation": equation or "",
                    "crops": crops,
                    "threshold": args.get("threshold", args.get("max_share",
                                          args.get("ratio", args.get("min_share", "")))),
                }
            )
    return pd.DataFrame(rows)


def constraint_group_matrix(table: pd.DataFrame, crops: list[str]) -> pd.DataFrame:
    """Rule x RPG group: how many of the group's fine crops each rule touches ("all" when the
    rule applies to every crop). Enabled rules only."""
    groups: dict[str, list[str]] = {}
    for crop in crops:
        try:
            groups.setdefault(base_group_for(crop), []).append(crop)
        except KeyError:
            continue
    ordered = sorted(groups)
    rows = {}
    for _, row in table[table["enabled"]].iterrows():
        key = row["label"] or f"{row['name']} #{row['position']}"
        if row["crops"] == "*":
            rows[key] = {group: "all" for group in ordered}
            continue
        touched = set(row["crops"])
        rows[key] = {
            group: (len(touched & set(members)) or "") for group, members in groups.items()
        }
    return pd.DataFrame.from_dict(rows, orient="index").reindex(columns=ordered).fillna("")


def rules_for_crop(table: pd.DataFrame, crop: str) -> pd.DataFrame:
    """Every rule that touches `crop` -- the question actually asked ("why no melon?")."""
    mask = table["crops"].apply(lambda crops: crops == "*" or crop in crops)
    return table[mask]


def eligibility_removals(dataset: Any, config: dict[str, Any]) -> dict[str, int]:
    """(plot, crop) pairs each enabled categorical rule forbids on its own, by label or name.

    Needs the real data. Rules overlap, so the counts do not add up to the pairs removed in
    total -- each says how much that rule alone takes away.
    """
    from core.data.eligibility import CATEGORICAL_RULE_REGISTRY

    plot_data = dataset.parameters["plot_data"]
    universe = set(dataset.sets["crops"])
    removals: dict[str, int] = {}
    for position, entry in enumerate(config.get("categorical_rules") or []):
        if not entry.get("enable", False):
            continue
        args = entry.get("args") or {}
        crops, condition = CATEGORICAL_RULE_REGISTRY[entry["name"]](plot_data, **args)
        affected = len(universe) if crops == "*" else len(universe & set(crops))
        key = args.get("label") or f"{entry['name']} #{position}"
        removals[key] = int(condition.sum()) * affected
    return removals


# ------------------------------------------------------------------- 3. parameter choices
_STEP = re.compile(r"^(?P<key>[A-Za-z0-9_]+)(\[(?P<selector>[^\]]+)\])?$")


def resolve_config_path(config: dict[str, Any], path: str) -> Any:
    """Value at `path` in the config. `list[label=x]`, `list[name=x]` and `list[0]` select
    within a list; raises KeyError with the failing step when the path does not resolve."""
    node: Any = config
    for step in path.split("."):
        match = _STEP.match(step)
        if not match or not isinstance(node, dict) or match["key"] not in node:
            raise KeyError(f"{path}: cannot resolve '{step}'")
        node = node[match["key"]]
        selector = match["selector"]
        if selector is None:
            continue
        if selector.isdigit():
            node = node[int(selector)]
            continue
        field, _, wanted = selector.partition("=")
        found = [
            item for item in node
            if (item.get("args") or {}).get(field) == wanted or item.get(field) == wanted
        ]
        if not found:
            raise KeyError(f"{path}: no entry with {field}={wanted}")
        node = found[0]
    return node


def _same(actual: Any, retained: Any) -> bool:
    try:
        return float(actual) == float(retained)
    except (TypeError, ValueError):
        return str(actual) == str(retained)


def parameter_table(config: dict[str, Any], path: Path = PARAMETER_CHOICES) -> pd.DataFrame:
    """One row per parameter: candidates, retained value, the value in config.yaml, and
    whether the two agree ("ok", "DRIFT", or "-" when the choice lives outside the config)."""
    rows = []
    for entry in _load_yaml(path).get("parameters") or []:
        in_config, check = None, "-"
        if entry.get("config"):
            try:
                in_config = resolve_config_path(config, entry["config"])
                check = "ok" if _same(in_config, entry["retained"]) else "DRIFT"
            except (KeyError, IndexError, TypeError):
                check = "path not found"
        rows.append(
            {
                "id": entry["id"],
                "parameter": entry["name"],
                "unit": entry.get("unit", ""),
                "candidates": "; ".join(
                    f"{c['value']} ({c['source']})" for c in entry.get("candidates") or []
                ),
                "retained": entry["retained"],
                "in_config": in_config if in_config is not None else "",
                "check": check,
                "status": entry.get("status", ""),
                "reason": " ".join(str(entry.get("reason", "")).split()),
                "vigilance": entry.get("vigilance", ""),
            }
        )
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------ 4. roadmap
def roadmap_table(path: Path = ROADMAP) -> pd.DataFrame:
    """The roadmap items, in file order, with their free-text fields flattened to one line."""
    items = _load_yaml(path).get("items") or []
    frame = pd.DataFrame(items)
    for column in ("left", "blocked_by", "title"):
        if column in frame:
            frame[column] = frame[column].fillna("").map(lambda text: " ".join(str(text).split()))
    for column in ("spec", "since"):
        if column not in frame:
            frame[column] = ""
    return frame.fillna("")


def roadmap_summary(roadmap: pd.DataFrame) -> pd.DataFrame:
    """Item counts, area x status."""
    return (
        roadmap.pivot_table(index="area", columns="status", values="id", aggfunc="count", fill_value=0)
        .reindex(columns=[s for s in ROADMAP_STATUSES if s in set(roadmap["status"])])
    )


# ------------------------------------------------------------------------------ rendering
_SYMBOLS = {REPORTED: "●", COMPUTABLE: "○", NEEDS_DEFINITION: "◐", NOT_APPLICABLE: "–"}


def _markdown_table(frame: pd.DataFrame, index_name: str | None = None) -> list[str]:
    columns = ([index_name] if index_name else []) + [str(c) for c in frame.columns]
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for key, row in frame.iterrows():
        cells = ([str(key)] if index_name else []) + [
            str(v).replace("|", "/") for v in row.tolist()
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render_markdown(
    *,
    levels: list[str],
    indicator_matrix: pd.DataFrame,
    constraints: pd.DataFrame,
    group_matrix: pd.DataFrame,
    parameters: pd.DataFrame,
    roadmap: pd.DataFrame,
    removals: dict[str, int] | None = None,
    generated_on: str = "",
) -> str:
    """The whole board as one Markdown document."""
    shown = indicator_matrix.copy()
    for level in levels:
        shown[level] = shown[level].map(_SYMBOLS)
    lines = [
        "# MOSAICA -- status board",
        "",
        f"_Generated by `scripts/build_status_board.py`{' on ' + generated_on if generated_on else ''}."
        " Do not edit by hand: edit the sources named in each section and regenerate._",
        "",
        "## 1. Indicators x aggregation levels",
        "",
        "Source: `case_studies/guadeloupe/status/indicator_catalog.yaml`. "
        "● reported by every run today · ○ computable from the data, not yet reported · "
        "◐ needs a definition at that level (non-additive statistic) · – not meaningful.",
        "",
        *_markdown_table(shown, "indicator"),
        "",
        "## 2. Constraints and eligibility rules",
        "",
        "Derived from `case_studies/guadeloupe/config.yaml` itself. `gams_equation` is filled only "
        "when the equation is found in `context/gams/`.",
        "",
    ]
    table = constraints.copy()
    table["crops"] = table["crops"].map(
        lambda crops: "all" if crops == "*" else f"{len(crops)}: " + ", ".join(crops[:6])
        + (" ..." if len(crops) > 6 else "")
    )
    if removals:
        table["pairs_removed"] = [
            removals.get(row["label"] or f"{row['name']} #{row['position']}", "")
            for _, row in table.iterrows()
        ]
    columns = ["section", "name", "label", "enabled", "role", "gams_equation", "threshold", "crops"]
    columns += ["pairs_removed"] if removals else []
    lines += _markdown_table(table[columns].set_index("section"), "section")
    lines += [
        "",
        "### Enabled rules x RPG crop groups",
        "",
        "Number of the group's fine crops each enabled rule touches; `all` = every crop.",
        "",
        *_markdown_table(group_matrix, "rule"),
        "",
        "## 3. Parameters with several plausible values",
        "",
        "Source: `case_studies/guadeloupe/status/parameter_choices.yaml`. `check` compares the "
        "retained value with the one in config.yaml: `DRIFT` means the file or the config is stale.",
        "",
        *_markdown_table(
            parameters[["parameter", "retained", "in_config", "check", "status", "candidates",
                        "reason"]].set_index("parameter"),
            "parameter",
        ),
        "",
        "## 4. Implementation roadmap",
        "",
        "Source: `docs/status/roadmap.yaml`.",
        "",
        *_markdown_table(roadmap_summary(roadmap), "area"),
        "",
    ]
    for status in ROADMAP_STATUSES:
        chunk = roadmap[roadmap["status"] == status]
        if chunk.empty:
            continue
        lines += [f"### {status.replace('_', ' ')}", ""]
        for _, item in chunk.iterrows():
            # An item can carry both: what remains, and what stops it moving.
            left, blocked_by = item.get("left") or "", item.get("blocked_by") or ""
            extra = " ".join(filter(None, [left, f"Blocked by: {blocked_by}" if left and blocked_by
                                           else blocked_by]))
            # STATUS.md sits in docs/status/, the spec paths are repo-relative.
            spec = f" ([spec](../../{Path(item['spec']).as_posix()}))" if item.get("spec") else ""
            lines.append(f"- **{item['id']}** ({item['area']}) -- {item['title']}{spec}"
                         + (f". {extra}" if extra else ""))
        lines.append("")
    return "\n".join(lines)
