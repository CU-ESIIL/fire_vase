"""Small mathematical fixtures, not a source of scientific observations."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest
from cubedynamics.analysis_v2 import fit_pca

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPTS))
from validate_fire_vase_science import geometry_similarity, null_growth, partial_rank, ridge_effects
from fire_vase_v2 import validate_fixed_protocol


def test_geometry_identity_on_shared_anchors():
    rng=np.random.default_rng(9)
    x=rng.dirichlet(np.ones(6),100);fit=fit_pca(x)
    pairs=rng.integers(0,100,(2,200))
    result=geometry_similarity(fit,fit,x,pairs,neighbors=5)
    for value in result.values():assert value==pytest.approx(1,abs=1e-10)


@pytest.mark.parametrize("name",["temporal_shuffle","dirichlet_1","dirichlet_10"])
def test_nulls_preserve_real_total_and_observation_count(name):
    g=np.array([2.,3.,7.,11.])
    a=null_growth(g,name,np.random.default_rng(8))
    b=null_growth(g,name,np.random.default_rng(8))
    assert np.array_equal(a,b)
    assert len(a)==len(g) and a.sum()==pytest.approx(g.sum())
    assert (a>=0).all()
    if name=="temporal_shuffle":assert np.array_equal(np.sort(a),np.sort(g))


def test_partial_rank_projects_both_outcomes_off_same_nuisance():
    x=np.array([1,3,4,2,5,7,6,8.]);y=np.array([3,1,2,5,4,8,7,6.])
    c=np.c_[np.ones(8),np.arange(8)]
    _,_,res=partial_rank(x,y,c)
    np.testing.assert_allclose(c.T@res,0,atol=1e-10)


def test_interaction_coefficient_units_and_cluster_error():
    x=np.linspace(-3,3,80)
    d=pd.DataFrame(dict(fire_id=np.repeat(np.arange(40),2),x=x,next_growth_log1p=2+3*x))
    beta,se=ridge_effects(d,["x"],alpha=0)
    assert beta[0]==pytest.approx(3)
    assert se[0]<1e-10


def test_fixed_protocol_rejects_silent_threshold_override():
    import json
    config=json.loads((SCRIPTS.parent/"config/analysis_v2.json").read_text())
    validate_fixed_protocol(config)
    with pytest.raises(ValueError,match="ignored override"):
        validate_fixed_protocol({**config,"primary_minimum_observations":7})
