from types import SimpleNamespace

from radar_intelligence.analysis import heuristic_analysis, heuristic_impact
from radar_intelligence.candidate import heuristic_candidate


def raw(title: str, content: str, source_type: str = "github_release"):
    return SimpleNamespace(title=title, content=content, source=SimpleNamespace(type=source_type))


def test_candidate_release_with_signals():
    d = heuristic_candidate("wgpu 25.0 released", "Adds WebGPU support, new backend for Vulkan 1.4", "wgpu", "github_release")
    assert d.candidate


def test_candidate_bugfix_rejected():
    d = heuristic_candidate("Fix typo in comment", "minor cleanup", "wgpu", "github_pr")
    assert not d.candidate


def test_analysis_release():
    a = heuristic_analysis(
        SimpleNamespace(name="wgpu", slug="wgpu", type="graphics_runtime"),
        [raw("wgpu 25.0.0 released", "New release adds Vulkan backend improvements. Breaking change: removed old API.")],
        [],
    )
    assert a.event_type in ("VERSION_RELEASE", "BREAKING_CHANGE")
    assert a.why_it_matters
    assert "测试" not in a.why_it_matters  # no placeholder text


def test_analysis_mobile_expansion_raises_impact():
    a = heuristic_analysis(
        SimpleNamespace(name="engine", slug="engine", type="game_engine"),
        [raw("Engine adds mesh shader support on Android and Windows", "experimental support, now stable")],
        [],
    )
    impact = heuristic_impact(a)
    assert impact.impact_level in ("High", "Critical")


def test_maturity_transition_detected():
    a = heuristic_analysis(
        SimpleNamespace(name="x", slug="x", type="technology"),
        [raw("Feature goes stable after experimental preview", "The feature is now production ready")],
        [],
    )
    assert a.maturity_from != a.maturity_to
