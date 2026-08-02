"""The reference runs: which output folder plays which role, from references.yaml.

The comparison page can show any (run, side) series, but three of them are not scenarios
among others -- the observed 2017 land use, the strict-GAMS calibration, and the retained
one. Declaring them in a versioned manifest rather than re-picking them from a dropdown on
every visit makes the choice explicit and reviewable, and carries the reason with it.

Pure and Streamlit-free: the page only wires these to widgets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_MANIFEST = Path("case_studies/guadeloupe/references.yaml")

_VALID_SIDES = ("input", "output")


@dataclass(frozen=True)
class Reference:
    """One declared reference. `run` is a folder name under outputs/, not a path."""

    id: str
    run: str
    side: str
    label: str
    note: str = ""
    # Metrics this reference is expected to reproduce, as {dotted recap path: value}, and
    # how far it may drift before that counts as a regression. Checked by
    # scripts/check_references.py; empty means "not guarded".
    expect: dict[str, float] = field(default_factory=dict)
    tolerance_pct: float = 2.0


@dataclass(frozen=True)
class ResolvedReference:
    """A reference matched (or not) against the folders actually present in outputs/."""

    reference: Reference
    run_dir: Path | None

    @property
    def missing(self) -> bool:
        return self.run_dir is None


def parse_references(document: dict[str, Any] | None) -> list[Reference]:
    """Manifest mapping -> ordered references, skipping malformed entries rather than
    raising: a typo in one entry must not blank the whole page.

    An entry needs `id` and `run`; `side` defaults to "output" (the allocation) and `label`
    to the id, so a minimal three-line entry is valid.
    """
    entries = (document or {}).get("references") or []
    references: list[Reference] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        identifier, run = entry.get("id"), entry.get("run")
        if not identifier or not run:
            continue
        side = str(entry.get("side") or "output")
        if side not in _VALID_SIDES:
            continue
        expect = entry.get("expect") or {}
        references.append(
            Reference(
                id=str(identifier),
                run=str(run),
                side=side,
                label=str(entry.get("label") or identifier),
                note=str(entry.get("note") or "").strip(),
                expect={str(k): float(v) for k, v in expect.items()},
                tolerance_pct=float(entry.get("tolerance_pct", 2.0)),
            )
        )
    return references


def load_references(manifest_path: Path) -> list[Reference]:
    """References declared in `manifest_path`, or [] when it is absent or unreadable.

    A missing manifest is a normal state (a fresh clone, another case study), not an error:
    the page falls back to its ordinary free-form series picker.
    """
    try:
        document = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return []
    return parse_references(document)


def resolve(references: list[Reference], outputs_root: Path) -> list[ResolvedReference]:
    """Pair each reference with its run folder, or None when that folder is absent.

    Missing folders are reported rather than dropped: "output_1 has not been re-run yet" is
    something the reader must see, not something to hide by silently showing two series
    where three were declared.
    """
    return [
        ResolvedReference(
            reference=reference,
            run_dir=(outputs_root / reference.run)
            if (outputs_root / reference.run).is_dir()
            else None,
        )
        for reference in references
    ]


def series_labels_for(
    resolved: list[ResolvedReference], catalog: dict[str, dict]
) -> dict[str, str]:
    """{reference id -> series label} for the references present in a page's series catalog.

    `catalog` is the page's own {label -> {run_dir, side, ...}} mapping, so this returns the
    exact keys the multiselect uses. A reference whose run is missing, or whose run carries
    no facts table for that side, is simply absent from the result.
    """
    by_coordinates = {
        (entry["run_dir"].name, entry["side"]): label for label, entry in catalog.items()
    }
    matched: dict[str, str] = {}
    for item in resolved:
        if item.run_dir is None:
            continue
        label = by_coordinates.get((item.run_dir.name, item.reference.side))
        if label is not None:
            matched[item.reference.id] = label
    return matched
