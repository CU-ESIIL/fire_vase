"""Methodological invariants; small explicit fixtures are tests, not scientific data."""
import numpy as np
import pandas as pd
import pytest
from cubedynamics.analysis_v2 import (CORE,TRAITS,growth_summary,allocation_profile,pulse_counts,
    neighborhood,fit_pca,exact_transitions,validate_exposure,predictor_sets,complete_cohort,
    splits,ridge_predict,unique_matches,evaluate_models,cohort_hash)


def test_peak_is_not_mean():
    s,p=growth_summary([1,8,3],3,12)
    assert s["peak_growth_km2_per_day"]==8
    assert s["mean_catalog_growth_km2_per_day"]==4
    assert p.sum()==1


def test_entropy_uses_reconstructed_total_not_catalog():
    s,p=growth_summary([2,2],4,10)
    assert s["normalized_entropy"]==pytest.approx(1)
    assert s["area_discrepancy_km2"]==-6
    assert s["reconstructed_area_km2"]==4
    assert p.sum()==1


@pytest.mark.parametrize("g",[[0,0],[np.nan,2],[-1,2]])
def test_undefined_growth_is_not_fabricated(g):
    s,p=growth_summary(g,2,1)
    assert not s["growth_valid"]
    assert np.isnan(s["normalized_entropy"])
    assert np.isnan(p).all()


def test_one_slice_has_zero_entropy_and_no_internal_history():
    s,p=growth_summary([3],1,3)
    assert s["normalized_entropy"]==0
    assert np.allclose(allocation_profile(p),np.ones(20)/20)
    assert neighborhood({**s,"observation_count":1})=="one observation"


def test_profiles_conserve_mass_and_scale_invariance():
    for n in [1,2,3,7,23]:
        p=np.arange(1,n+1,dtype=float);p/=p.sum()
        for b in [10,20,40]:
            assert allocation_profile(p,b).sum()==pytest.approx(1)
            assert (allocation_profile(p,b)>=0).all()
    with pytest.raises(ValueError):allocation_profile([.1,.1])


def test_pulses_require_detected_maxima_not_observation_count():
    assert pulse_counts(np.ones(6))==(1,0)
    assert pulse_counts([4,0,0,4])==(2,1)
    row=dict(growth_valid=True,observation_count=6,consecutive=True,pulse_count=1,
             peak_timing=.5,front_loaded_fraction=.5,terminal_taper_fraction=1)
    assert neighborhood(row)=="distributed growth"
    assert neighborhood({**row,"pulse_count":2})=="multiple detected pulses"


def sample_slices():
    return pd.DataFrame(dict(fire_id=["a"]*4+["b"]*2,slice_index=[0,1,2,3,0,1],
        timestamp=["2020-01-01","2020-01-02","2020-01-04","2020-01-05","2020-02-01",None],
        ring_area_km2=[1,3,7,9,2,4],climate_available=[True,False,True,True,True,True]))


def test_exact_calendar_day_before_weather_filtering():
    d,a=exact_transitions(sample_slices())
    assert len(d)==2
    assert d.next_growth_km2.tolist()==[3,9]
    assert a["one_day_transitions"]==2
    assert a["longer_gaps"]==1
    assert a["missing_dates"]==1
    assert d.previous_growth_km2.isna().all() # gap is not previous-day zero


def test_duplicate_dates_are_excluded():
    s=sample_slices();s.loc[2,"timestamp"]="2020-01-02"
    d,a=exact_transitions(s)
    assert a["duplicate_date_rows"]==2
    assert d.empty


def test_no_final_geometry_or_future_geometry_in_prospective_models():
    d=pd.DataFrame(dict(exposure_geometry=["day_t_newly_burned_centroid"],
        timestamp=["2020-01-01"],geometry_max_date=["2020-01-01"]))
    validate_exposure(d)
    with pytest.raises(ValueError):validate_exposure(d.assign(exposure_geometry="final_event_centroid"))
    with pytest.raises(ValueError):validate_exposure(d.assign(geometry_max_date="2020-01-02"))


def test_predictor_sets_nested_and_complete_cohort_identical():
    sets=predictor_sets()
    assert set(sets["core_means"])<set(sets["core_plus_max"])
    assert set(sets["core_means"])<set(sets["comprehensive_means"])
    assert set(sets["comprehensive_means"])<set(sets["comprehensive_plus_max"])
    assert "max_vpd" not in sets["core_means"]+sets["comprehensive_means"]
    cols=set(sum(sets.values(),[]))
    d=pd.DataFrame({c:[1.,2.,3.] for c in cols})
    d["fire_id"]=["a","b","c"];d["response"]=[1,2,3]
    d.loc[1,"q90_vpd"]=np.nan
    common=complete_cohort(d,sets,["response"])
    assert common.fire_id.tolist()==["a","c"]
    assert len({cohort_hash(common) for _ in sets})==1


def test_pca_and_scaling_are_fitted_only_to_training_data():
    x=np.array([[0.,1.],[1.,4.],[3.,0.]])
    fit=fit_pca(x)
    assert np.allclose(fit.transform(x).mean(0),0)
    assert np.allclose(fit.mean,x.mean(0))
    test=np.array([[10000.,20000.]])
    _,mu,sd=ridge_predict(x,test,np.array([[1.],[2.],[4.]]))
    assert np.allclose(mu,x.mean(0))
    assert not np.allclose(mu,np.r_[x,test].mean(0))


@pytest.mark.parametrize("kind",["random_fire","year_block","region_block","spatiotemporal"])
def test_group_safe_folds_and_explicit_spatiotemporal_buffer(kind):
    d=pd.DataFrame(dict(fire_id=["a","a","b","b","c","c"],year=[2001,2001,2008,2008,2015,2015],
                        region=["west","west","east","east","west","west"]))
    for _,train,test in splits(d,kind):
        assert not set(d.loc[train,"fire_id"])&set(d.loc[test,"fire_id"])
        if kind=="spatiotemporal" and test.any():
            assert not set(d.loc[train,"region"])&set(d.loc[test,"region"])
            assert not set(d.loc[train,"year"]//5)&set(d.loc[test,"year"]//5)


def matching_fixture():
    return pd.DataFrame(dict(fire_id=list("abcdef"),region=["west"]*6,season=["JJA"]*6,
        duration_days=[3]*6,observation_count=[3]*6,catalog_area_km2=[2,2,2,2,100,100],
        x=[0,.01,1,1.01,3,3.01]))


def test_matching_calipers_unique_partners_and_determinism():
    d=matching_fixture()
    a,_=unique_matches(d,["x"],k=5,caliper=.2)
    b,_=unique_matches(d,["x"],k=5,caliper=.2)
    pd.testing.assert_frame_equal(a,b)
    assert (a.match_distance<=a.caliper).all()
    assert not pd.concat([a.fire_id_a,a.fire_id_b]).duplicated().any()
    assert a.log_area_distance.le(np.log(2)).all()


def test_matching_does_not_select_discordant_outcomes():
    d=matching_fixture();a,_=unique_matches(d,["x"])
    d["unused_outcome"]=[100,0,1000,1,99,3]
    b,_=unique_matches(d,["x"])
    pd.testing.assert_frame_equal(a,b)


def test_model_output_determinism_and_common_rows():
    n=60
    d=pd.DataFrame(dict(fire_id=[str(i) for i in range(n)],year=np.repeat([2001,2008,2015],20),
        region=np.tile(["west","east"],30),x=np.linspace(0,1,n),y=np.sin(np.arange(n))))
    kwargs=dict(alphas=(1.,),reps=5,kinds=["random_fire"])
    a=evaluate_models(d,{"mean_only":[],"x":["x"]},["y"],**kwargs)
    b=evaluate_models(d,{"mean_only":[],"x":["x"]},["y"],**kwargs)
    for i in range(4):pd.testing.assert_frame_equal(a[i],b[i])
    assert a[0].cohort_hash.nunique()==1
    assert a[0].n.nunique()==1


def test_foldwise_pca_preprocessing_and_zero_global_target_use():
    n=80
    d=pd.DataFrame(dict(fire_id=[str(i) for i in range(n)],year=[2001]*n,region=["west"]*n,
        x=np.arange(n),y=np.sin(np.arange(n))))
    for j in range(4):d[f"p{j}"]=np.cos(np.arange(n)/(j+1))
    outputs=evaluate_models(d,{"mean_only":[],"x":["x"]},["y"],profile_columns=["p0","p1","p2","p3"],
        alphas=(1.,),reps=5,kinds=["random_fire"])
    prep=outputs[3]
    for fold,train,test in splits(d,"random_fire"):
        row=prep[(prep.fold==fold)&(prep.stage=="outcome_pca")&(prep.feature=="p0")].iloc[0]
        assert row.center==pytest.approx(d.loc[train,"p0"].mean())


def test_known_duration_outcome_is_not_reported_as_predictive_skill():
    n=40
    d=pd.DataFrame(dict(fire_id=[str(i) for i in range(n)],year=[2001]*n,region=["west"]*n,
        log_duration=np.linspace(0,1,n)))
    results,*_=evaluate_models(d,{"mean_only":[],"length_only":["log_duration"]},["log_duration"],
        alphas=(1.,),reps=5,kinds=["random_fire"])
    row=results[results.predictor_set.eq("length_only")].iloc[0]
    assert row.status=="excluded_known_outcome"
    assert np.isnan(row.r2)
