"""The guard on the reference runs' headline figures. Data-free; no solve."""

import json

import yaml

from apps.dashboard import references
from scripts import check_references


def _reference(**overrides):
    entry = {
        "id": "retained", "run": "calib_retenu", "side": "output", "label": "Calib retenu",
        "tolerance_pct": 5.0,
        "expect": {"calibration.regional_pad_pct": 6.60, "objective.value": 81222224},
    }
    entry.update(overrides)
    return references.parse_references({"references": [entry]})[0]


def _run(root, name, recap):
    run_dir = root / name
    run_dir.mkdir(parents=True)
    (run_dir / "recap.json").write_text(json.dumps(recap), encoding="utf-8")
    return run_dir


def test_resolve_metric_walks_a_dotted_recap_path():
    recap = {"calibration": {"regional_pad_pct": 6.6}, "objective": {"value": 8.1e7}}

    assert check_references.resolve_metric(recap, "calibration.regional_pad_pct") == 6.6
    assert check_references.resolve_metric(recap, "objective.value") == 8.1e7


def test_resolve_metric_returns_none_rather_than_raising_on_a_missing_path():
    """Missing is distinct from wrong: a run predating a recap block has nothing to compare."""
    assert check_references.resolve_metric({}, "calibration.regional_pad_pct") is None
    assert check_references.resolve_metric({"calibration": 3}, "calibration.x") is None
    assert check_references.resolve_metric({"a": {"b": "texte"}}, "a.b") is None


def test_values_within_the_band_pass(tmp_path):
    run = _run(tmp_path, "calib_retenu", {
        "calibration": {"regional_pad_pct": 6.63}, "objective": {"value": 81230000},
    })

    rows = check_references.check_reference(_reference(), run)

    assert {row["status"] for row in rows} == {"ok"}


def test_the_band_is_wide_enough_for_measured_solver_noise(tmp_path):
    """Three HiGHS seeds give PAD 48.44 / 48.29 / 48.31 -- 0.15 point, 2.3 % relative on the
    smallest guarded value. An exact-match guard would fail on a re-run that changed nothing."""
    run = _run(tmp_path, "calib_retenu", {
        "calibration": {"regional_pad_pct": 6.60 + 0.15}, "objective": {"value": 81222224},
    })

    rows = check_references.check_reference(_reference(), run)

    assert {row["status"] for row in rows} == {"ok"}


def test_a_real_drift_is_flagged(tmp_path):
    run = _run(tmp_path, "calib_retenu", {
        "calibration": {"regional_pad_pct": 12.0}, "objective": {"value": 81222224},
    })

    rows = check_references.check_reference(_reference(), run)
    drifted = [row for row in rows if row["status"] == "drift"]

    assert [row["metric"] for row in drifted] == ["calibration.regional_pad_pct"]
    assert drifted[0]["drift_pct"] > 5.0


def test_a_metric_absent_from_the_recap_reads_as_missing_not_as_a_drift(tmp_path):
    run = _run(tmp_path, "calib_retenu", {"objective": {"value": 81222224}})

    rows = check_references.check_reference(_reference(), run)
    by_metric = {row["metric"]: row["status"] for row in rows}

    assert by_metric["calibration.regional_pad_pct"] == "missing"
    assert by_metric["objective.value"] == "ok"


def test_an_absent_run_folder_is_reported_for_every_guarded_metric():
    rows = check_references.check_reference(_reference(), None)

    assert {row["status"] for row in rows} == {"no run"}
    assert len(rows) == 2


def test_an_expected_value_of_zero_falls_back_to_absolute_drift(tmp_path):
    """A relative drift is undefined against 0, so the band is read in the metric's own
    units there. 3 units stays inside a band of 5; 9 does not."""
    reference = _reference(expect={"calibration.regional_pad_pct": 0.0})

    near = check_references.check_reference(
        reference, _run(tmp_path / "a", "calib_retenu",
                        {"calibration": {"regional_pad_pct": 3.0}})
    )
    far = check_references.check_reference(
        reference, _run(tmp_path / "b", "calib_retenu",
                        {"calibration": {"regional_pad_pct": 9.0}})
    )

    assert (near[0]["drift_pct"], near[0]["status"]) == (3.0, "ok")
    assert (far[0]["drift_pct"], far[0]["status"]) == (9.0, "drift")


def test_main_exits_non_zero_when_a_reference_drifts(tmp_path, capsys):
    manifest = tmp_path / "references.yaml"
    manifest.write_text(yaml.safe_dump({"references": [{
        "id": "retained", "run": "calib_retenu", "side": "output", "label": "Calib retenu",
        "tolerance_pct": 5.0, "expect": {"calibration.regional_pad_pct": 6.60},
    }]}), encoding="utf-8")
    outputs = tmp_path / "outputs"
    _run(outputs, "calib_retenu", {"calibration": {"regional_pad_pct": 40.0}})

    code = check_references.main(
        ["--references", str(manifest), "--outputs", str(outputs)]
    )

    assert code == 1
    assert "ÉCART" in capsys.readouterr().out


def test_main_exits_zero_when_everything_holds(tmp_path):
    manifest = tmp_path / "references.yaml"
    manifest.write_text(yaml.safe_dump({"references": [{
        "id": "retained", "run": "calib_retenu", "side": "output", "label": "Calib retenu",
        "expect": {"calibration.regional_pad_pct": 6.60},
    }]}), encoding="utf-8")
    outputs = tmp_path / "outputs"
    _run(outputs, "calib_retenu", {"calibration": {"regional_pad_pct": 6.60}})

    assert check_references.main(
        ["--references", str(manifest), "--outputs", str(outputs)]
    ) == 0


def test_the_shipped_manifest_declares_expectations_for_both_calibrations():
    """The whole point of the guard is that the published figures are the guarded ones."""
    declared = {r.id: r for r in references.load_references(references.DEFAULT_MANIFEST)}

    for key in ("gams_parity", "retained"):
        assert declared[key].expect, f"{key} doit porter un bloc expect:"
        assert "calibration.regional_pad_pct" in declared[key].expect
        assert declared[key].tolerance_pct >= 2.5, "sous le bruit de solveur mesuré"
