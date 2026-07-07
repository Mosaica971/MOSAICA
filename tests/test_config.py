import pytest
import yaml

from core.config import load_config, resolve_enabled


def test_load_config_parses_yaml_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"solver": {"name": "appsi_highs", "args": {}}}))

    config = load_config(config_path)

    assert config == {"solver": {"name": "appsi_highs", "args": {}}}


def test_resolve_enabled_returns_only_enabled_entries_paired_with_args():
    registry = {"foo": lambda **kwargs: kwargs, "bar": lambda **kwargs: kwargs}
    entries = [
        {"name": "foo", "enable": True, "args": {"x": 1}},
        {"name": "bar", "enable": False, "args": {"y": 2}},
    ]

    resolved = resolve_enabled(entries, registry)

    assert len(resolved) == 1
    fn, args = resolved[0]
    assert fn is registry["foo"]
    assert args == {"x": 1}


def test_resolve_enabled_defaults_missing_args_to_empty_dict():
    registry = {"foo": lambda **kwargs: kwargs}
    entries = [{"name": "foo", "enable": True}]

    resolved = resolve_enabled(entries, registry)

    assert resolved == [(registry["foo"], {})]


def test_resolve_enabled_raises_key_error_for_unknown_name():
    registry = {"foo": lambda **kwargs: kwargs}
    entries = [{"name": "unknown", "enable": True}]

    with pytest.raises(KeyError, match="unknown"):
        resolve_enabled(entries, registry)
