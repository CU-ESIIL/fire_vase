#!/usr/bin/env python3
"""Validate actual v2 outputs and compare a saved fixed-seed regeneration snapshot."""
from pathlib import Path
import argparse
import json
import sys
import numpy as np
import pandas as pd
from fire_vase_v2_inputs import sha256

ROOT=Path(__file__).resolve().parents[1]


def fingerprints():
    paths=[]
    for p in (ROOT/"analysis/v2").iterdir():
        if p.suffix in [".csv",".parquet",".gz"] and p.name!="issue_audit.csv":paths.append(p)
    paths+=list((ROOT/"figures/v2").glob("*.png"))+list((ROOT/"figures/v2").glob("*.pdf"))+list((ROOT/"figures/v2").glob("*.svg"))
    paths+=[ROOT/"output/pdf/fire_vase_v2_manuscript.pdf",ROOT/"docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md"]
    return {str(p.relative_to(ROOT)):sha256(p) for p in sorted(paths)}


def verify():
    out=ROOT/"analysis/v2"
    d=pd.read_parquet(out/"event_analysis.parquet")
    profiles=[c for c in d if c.startswith("allocation_")]
    primary=d[d.primary_eligible]
    assert primary.observation_count.ge(3).all() and primary.consecutive.all()
    assert np.allclose(primary[profiles].sum(1),1)
    assert primary.normalized_entropy.between(-1e-12,1+1e-12).all()
    assert primary.peak_growth_km2_per_day.ge(primary.mean_observed_growth_km2_per_day-1e-10).all()
    loadings=pd.read_csv(out/"pca_loadings.csv")
    assert loadings.feature.tolist()==profiles
    assert not any("area" in c or "duration" in c or "count" in c for c in loadings.feature)
    for kind in ["event","state"]:
        result=pd.read_csv(out/f"{kind}_performance.csv")
        assert result.cohort_hash.nunique()==1
        assert result.cohort_n.nunique()==1
        assert result.groupby(["kind","alpha"]).n.nunique().eq(1).all()
        if "status" in result:
            assert result.loc[result.status.eq("excluded_known_outcome"),"r2"].isna().all()
    s=pd.read_parquet(out/"day_t_weather.parquet")
    assert s.exposure_geometry.eq("day_t_newly_burned_centroid").all()
    assert pd.to_datetime(s.geometry_max_date).le(pd.to_datetime(s.timestamp)).all()
    pairs=pd.read_csv(out/"matched_pairs.csv")
    for _,g in pairs.groupby("matching_space"):
        assert not pd.concat([g.fire_id_a,g.fire_id_b]).duplicated().any()
        assert g.match_distance.le(g.caliper+1e-10).all()
        assert g.log_area_distance.le(np.log(2)+1e-10).all()
        for c in ["region","season","duration_days","observation_count"]:
            assert g[c+"_a"].eq(g[c+"_b"]).all()
    assert pd.read_csv(out/"neighborhood_rules.csv").n.sum()==len(d)
    return {"scientific_invariants":"pass","primary_events":len(primary),"event_model_cohort":len(pd.read_parquet(out/"event_cohort.parquet")),
            "state_model_rows":len(pd.read_parquet(out/"state_cohort.parquet")),"pairs_checked":len(pairs)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot",type=Path)
    parser.add_argument("--compare",type=Path)
    args=parser.parse_args()
    results=verify()
    if args.snapshot:
        args.snapshot.write_text(json.dumps(fingerprints(),indent=2))
        results["snapshot_files"]=len(fingerprints())
    if args.compare:
        previous=json.loads(args.compare.read_text());current=fingerprints()
        changes=[p for p in previous if previous[p]!=current.get(p)]
        added=sorted(set(current)-set(previous))
        results.update(deterministic_regeneration="pass" if not changes and not added else "fail",
                       compared_files=len(previous),changed_files=changes,added_files=added)
    (ROOT/"analysis/v2/verification.json").write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))
    if results.get("deterministic_regeneration")=="fail":return 1
    return 0


if __name__=="__main__":sys.exit(main())
