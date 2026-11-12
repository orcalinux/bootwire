# desktop/tests/test_config.py

import pytest

from bootwire.config import load_config


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.delenv("BOOTWIRE_CONFIG", raising=False)


def test_defaults():
    cfg = load_config()
    assert cfg["general"] == {"timeout": 0.5, "erase_timeout": 5.0, "max_retries": 3}
    assert cfg["serial"] == {"port": None, "baudrate": 115200}


def test_local_file_overrides_every_section(tmp_path):
    (tmp_path / "bootwire.yaml").write_text(
        "general:\n  max_retries: 7\nserial:\n  port: /dev/ttyACM1\n  baudrate: 921600\n"
    )
    cfg = load_config()
    assert cfg["general"]["max_retries"] == 7
    assert cfg["general"]["timeout"] == 0.5
    assert cfg["serial"] == {"port": "/dev/ttyACM1", "baudrate": 921600}


def test_unknown_and_empty_keys_are_ignored(tmp_path):
    (tmp_path / "bootwire.yaml").write_text("serial:\n  port:\n  colour: blue\ntcp:\n  host: x\n")
    cfg = load_config()
    assert cfg["serial"] == {"port": None, "baudrate": 115200}
    assert "tcp" not in cfg


def test_env_var_wins_over_local_file(tmp_path, monkeypatch):
    (tmp_path / "bootwire.yaml").write_text("general:\n  timeout: 1.0\n")
    other = tmp_path / "other.yaml"
    other.write_text("general:\n  timeout: 2.0\n")
    monkeypatch.setenv("BOOTWIRE_CONFIG", str(other))
    assert load_config()["general"]["timeout"] == 2.0


def test_explicit_path_wins(tmp_path):
    explicit = tmp_path / "explicit.yaml"
    explicit.write_text("general:\n  timeout: 3.0\n")
    assert load_config(str(explicit))["general"]["timeout"] == 3.0


def test_broken_yaml_falls_back_to_defaults(tmp_path):
    (tmp_path / "bootwire.yaml").write_text("general: [unclosed\n")
    assert load_config()["general"]["timeout"] == 0.5
