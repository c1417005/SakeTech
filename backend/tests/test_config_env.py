"""Env-override helpers for [TBD] thresholds: parse valid, fall back safely,
and keep defaults unchanged when env is unset."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config  # noqa: E402


def test_env_int_parses_and_falls_back(monkeypatch):
    monkeypatch.setenv("KUMU_TEST_INT", "42")
    assert config._env_int("KUMU_TEST_INT", 7) == 42
    monkeypatch.setenv("KUMU_TEST_INT", "  9 ")
    assert config._env_int("KUMU_TEST_INT", 7) == 9
    monkeypatch.setenv("KUMU_TEST_INT", "not-a-number")
    assert config._env_int("KUMU_TEST_INT", 7) == 7   # invalid -> default
    monkeypatch.setenv("KUMU_TEST_INT", "")
    assert config._env_int("KUMU_TEST_INT", 7) == 7   # blank -> default
    monkeypatch.delenv("KUMU_TEST_INT", raising=False)
    assert config._env_int("KUMU_TEST_INT", 7) == 7   # unset -> default


def test_env_float_parses_and_falls_back(monkeypatch):
    monkeypatch.setenv("KUMU_TEST_FLOAT", "0.55")
    assert config._env_float("KUMU_TEST_FLOAT", 0.3) == 0.55
    monkeypatch.setenv("KUMU_TEST_FLOAT", "oops")
    assert config._env_float("KUMU_TEST_FLOAT", 0.3) == 0.3
    monkeypatch.delenv("KUMU_TEST_FLOAT", raising=False)
    assert config._env_float("KUMU_TEST_FLOAT", 0.3) == 0.3


def test_defaults_unchanged_when_env_unset():
    # Guards that externalization did not alter the provisional defaults.
    assert config.VIEWING_SEC == 4
    assert config.HESITATING_SEC == 20
    assert config.BASIS_MIN_DWELL_SEC == 5
    assert config.MAX_PROFILE_TAGS == 3
    assert config.MAX_BASIS == 3
    assert config.CONF_HIGH_BASIS == 3
    assert config.CONF_HIGH_DWELL == 30
    assert config.CONF_MED_BASIS == 2
    assert config.CONF_MED_DWELL == 12
    assert config.AROMA_HIGH == 0.30
    assert config.BODY_RICH == 0.40
