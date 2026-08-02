"""Resolving WHICH case study a run is about.

`core/` speaks no Guadeloupe -- but until now every entry point did, in an import:
`from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset`. A second case
study therefore meant editing `main.py` and half of `scripts/`. This resolves the same three
functions by NAME, at call time, so the name lives in one flag instead of a dozen imports.

A case study is a package under `case_studies/` exposing exactly this contract:

    pipeline/data_pipeline.py   build_dataset(config) -> Dataset
    model/model.py              build_model(dataset, config) -> pyo.ConcreteModel
    reporting/report.py         generate_report(dataset, config, model, results, duration,
                                                *, outputs_root) -> Path
    config.yaml                 the reference config

Nothing else is required, and nothing else is called from outside. `model/model.py` is
imported as a MODULE on purpose: importing the package alone runs an empty `__init__.py` and
registers none of the case study's constraints (see `core/model/registry.py`).

Selection order: the explicit argument, then `$MOSAICA_CASE_STUDY`, then `guadeloupe`. The
default is a default, not an assumption -- `available()` lists what is actually on disk, and
an unknown name says so rather than raising a bare ImportError.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

CASE_STUDIES_ROOT = Path(__file__).resolve().parents[1] / "case_studies"
ENV_VAR = "MOSAICA_CASE_STUDY"
DEFAULT_CASE_STUDY = "guadeloupe"


@dataclass(frozen=True)
class CaseStudy:
    """The three callables and the paths an entry point needs, nothing more."""

    name: str
    build_dataset: Callable[[dict[str, Any]], Any]
    build_model: Callable[[Any, dict[str, Any]], Any]
    generate_report: Callable[..., Path]

    @property
    def dir(self) -> Path:
        return CASE_STUDIES_ROOT / self.name

    @property
    def config_path(self) -> Path:
        return self.dir / "config.yaml"


def available() -> list[str]:
    """Case-study package names present on disk, in alphabetical order."""
    if not CASE_STUDIES_ROOT.is_dir():
        return []
    return sorted(
        entry.name
        for entry in CASE_STUDIES_ROOT.iterdir()
        if entry.is_dir() and (entry / "config.yaml").is_file()
    )


def resolve_name(name: str | None = None) -> str:
    return name or os.environ.get(ENV_VAR) or DEFAULT_CASE_STUDY


def load(name: str | None = None) -> CaseStudy:
    """Import a case study's three entry points. Raises with the available names on a typo."""
    name = resolve_name(name)
    if not (CASE_STUDIES_ROOT / name / "config.yaml").is_file():
        listed = ", ".join(available()) or "(none)"
        raise KeyError(
            f"Unknown case study '{name}': no case_studies/{name}/config.yaml. "
            f"Available: {listed}"
        )

    def entry(module: str, function: str) -> Callable:
        return getattr(importlib.import_module(f"case_studies.{name}.{module}"), function)

    return CaseStudy(
        name=name,
        build_dataset=entry("pipeline.data_pipeline", "build_dataset"),
        # The module, never the package: `case_studies.<x>.model` is an empty __init__ and
        # would register no constraint, so every config naming one would raise KeyError.
        build_model=entry("model.model", "build_model"),
        generate_report=entry("reporting.report", "generate_report"),
    )


def add_argument(parser: Any) -> None:
    """Add the standard `--case-study` flag. One definition, so every script spells it the
    same way and reports the same available names."""
    parser.add_argument(
        "--case-study",
        default=None,
        help=f"Case study to run (default: ${ENV_VAR} or '{DEFAULT_CASE_STUDY}'). "
        f"Available: {', '.join(available()) or '(none)'}",
    )
