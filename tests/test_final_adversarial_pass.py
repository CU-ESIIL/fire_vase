import numpy as np

from final_adversarial_pass import boundary_metrics, histories_to_arrays, null_history


def test_temporal_shuffle_preserves_multiset_and_total():
    history = np.array([1.0, 4.0, 2.0, 3.0])
    shuffled = null_history(history, "temporal_shuffle", np.random.default_rng(9))
    np.testing.assert_array_equal(np.sort(shuffled), np.sort(history))
    assert shuffled.sum() == history.sum()


def test_dirichlet_null_preserves_length_total_and_positivity():
    history = np.array([1.0, 4.0, 2.0, 3.0])
    for condition in ["dirichlet_1", "dirichlet_10"]:
        simulated = null_history(history, condition, np.random.default_rng(11))
        assert len(simulated) == len(history)
        assert (simulated > 0).all()
        np.testing.assert_allclose(simulated.sum(), history.sum(), atol=1e-14)


def test_profiles_conserve_mass_and_boundary_metrics_are_explicit():
    histories = [np.array([6.0, 3.0, 1.0]), np.array([1.0, 2.0, 3.0, 4.0])]
    traits, profiles = histories_to_arrays(histories)
    np.testing.assert_allclose(profiles.sum(axis=1), 1.0, atol=1e-14)
    assert np.isfinite(traits.to_numpy()).all()
    metrics = boundary_metrics(histories[0])
    assert metrics["maximum_is_first"] == 1.0
    assert metrics["maximum_is_final"] == 0.0
    np.testing.assert_allclose(metrics["boundary_fraction"], 0.7)
