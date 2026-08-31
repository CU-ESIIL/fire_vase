"""Deterministic checks for the frozen Fire VASE Hellinger sensitivity."""
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compositional_sensitivity as composition


@pytest.fixture(scope="module")
def allocations():
    frame = pd.read_parquet(ROOT / "analysis/v2/event_features.parquet")
    primary = frame[frame.primary_eligible].sort_values("fire_id")
    return primary[composition.FEATURES].to_numpy(float)


def test_primary_allocations_are_finite_nonnegative_and_sum_to_one(allocations):
    assert allocations.shape == (10246, 20)
    assert np.isfinite(allocations).all()
    assert (allocations >= 0).all()
    np.testing.assert_allclose(allocations.sum(axis=1), 1.0, atol=2e-12, rtol=0)


def test_square_root_allocations_have_unit_squared_norm(allocations):
    _, transformed = composition.fit_hellinger(allocations)
    np.testing.assert_allclose(np.square(transformed).sum(axis=1), 1.0, atol=2e-12, rtol=0)


def test_frozen_baseline_variance_is_reproduced(allocations):
    baseline = composition.fit_baseline(allocations)
    checks = composition.reproduce_baseline(allocations, baseline)
    assert checks["sample_size_status"] == "pass"
    assert checks["pc1_status"] == "pass"
    assert checks["first_five_status"] == "pass"
    assert baseline.explained[0] == pytest.approx(0.341495575686, abs=2e-12)
    assert baseline.explained[:5].sum() == pytest.approx(0.894435897825, abs=2e-12)


def test_component_orientation_is_deterministic():
    scores = np.array([[1.0, 2.0], [-1.0, -2.0]])
    loadings = np.array([[-0.9, 0.1], [0.2, -0.8], [0.1, 0.3]])
    first_scores, first_loadings = composition.orient_components(scores, loadings)
    second_scores, second_loadings = composition.orient_components(scores, loadings)
    np.testing.assert_array_equal(first_scores, second_scores)
    np.testing.assert_array_equal(first_loadings, second_loadings)
    for axis in range(first_loadings.shape[1]):
        pivot = np.argmax(np.abs(first_loadings[:, axis]))
        assert first_loadings[pivot, axis] > 0


def test_headline_outputs_regenerate_byte_stably(tmp_path, monkeypatch):
    monkeypatch.setattr(composition, "OUT", tmp_path)
    first = composition.run()
    second = composition.run()
    assert first["outputs"] == second["outputs"]
    assert first["axis_correlations"] == second["axis_correlations"]
    assert first["anchor_pair_distance_spearman_5d"] == second["anchor_pair_distance_spearman_5d"]
    assert first["anchor_15_neighbor_overlap_5d"] == second["anchor_15_neighbor_overlap_5d"]
    assert all((tmp_path / name).exists() for name in first["outputs"])
