from types import SimpleNamespace

from radar_intelligence.rule_filter import classify_noise


def item(title: str, content: str = ""):
    return SimpleNamespace(title=title, content=content)


def test_dependency_bump_ignored():
    is_noise, reason = classify_noise(item("Bump vite from 5.1.0 to 5.1.2"))
    assert is_noise and reason == "noise:dependency_bump"


def test_ci_fix_ignored():
    is_noise, reason = classify_noise(item("Fix CI workflow failure on macOS runner"))
    assert is_noise and reason == "noise:ci_only"


def test_typo_ignored():
    is_noise, _ = classify_noise(item("Fix typo in README"))
    assert is_noise


def test_bugfix_ignored():
    is_noise, _ = classify_noise(item("Fix crash when closing window"))
    assert is_noise


def test_new_backend_not_ignored_despite_noise_words():
    text = "Release 4.1: Add WebGPU backend with initial support and fix typo in docs"
    is_noise, _ = classify_noise(item(text))
    assert not is_noise


def test_spec_extension_not_ignored():
    is_noise, _ = classify_noise(item("Add VK_KHR_maintenance5 extension support"))
    assert not is_noise


def test_plain_release_not_ignored():
    is_noise, _ = classify_noise(item("Godot 4.3 is out", "Major release with new features"))
    assert not is_noise


def test_hiring_ignored():
    is_noise, _ = classify_noise(item("We're hiring a graphics engineer"))
    assert is_noise
