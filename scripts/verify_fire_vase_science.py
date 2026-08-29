#!/usr/bin/env python3
"""Check final evidence, then snapshot/compare deterministic artifacts and freeze hashes."""
from pathlib import Path
import argparse
import json
import subprocess
import numpy as np
import pandas as pd
from fire_vase_v2_inputs import sha256
from verify_fire_vase_v2 import verify as verify_v2

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"analysis/scientific_validation"


def fingerprints():
    files=list(OUT.glob("*.csv"))
    files += [p for p in OUT.glob("*.md") if p.name!="verification.md"]
    files += [p for p in (ROOT/"figures/v2").iterdir() if p.suffix in [".png",".svg",".pdf",".md"]]
    files += [ROOT/"docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md",
              ROOT/"output/pdf/fire_vase_v2_manuscript.pdf"]
    return {str(p.relative_to(ROOT)):sha256(p) for p in sorted(files)}


def verify():
    result=verify_v2()
    claims=pd.read_csv(OUT/"final_claim_matrix.csv")
    assert claims.claim_id.tolist()==list("ABCDEFGHIJKLM")
    assert claims.status.isin(["SUPPORTED","SUPPORTED WITH CAVEATS","NOT YET SUPPORTED","NOT SUPPORTED"]).all()
    audit=pd.read_csv(OUT/"second_pass_audit.csv")
    assert audit.status.isin(["CORRECTLY IMPLEMENTED","PARTIALLY IMPLEMENTED","NOT IMPLEMENTED","IMPLEMENTED BUT SCIENTIFICALLY PROBLEMATIC"]).all()
    null=pd.read_csv(OUT/"null_history_comparison.csv")
    entropy=null.query("null=='temporal_shuffle' and metric=='normalized_entropy_mean'").iloc[0]
    assert abs(entropy.difference)<1e-10
    assert pd.read_csv(OUT/"null_sample.csv").fire_id.nunique()==4000
    assert pd.read_csv(OUT/"stability_anchors.csv").fire_id.nunique()==1000
    for name in ["event","state"]:
        replay=json.loads((OUT/f"{name}_replay.json").read_text())
        assert replay["status"]=="pass"
    d=pd.read_csv(OUT/"vpd_joint_density.csv")
    assert d.groupby("state").n.sum().eq(87944).all()
    perf=pd.read_csv(OUT/"weather_response_validation.csv")
    assert perf.cohort_hash.nunique()==1 and perf.n.eq(9212).all()
    for dimension in ["kind","fold"]:
        assert pd.read_csv(OUT/"event_fold_replay.csv")[dimension].notna().all()
    # Match manuscript's generated numbers to the controlling summary/table rows.
    summary=json.loads((OUT/"validated_summary.json").read_text())
    source=(ROOT/"docs/manuscripts/fire_vase_developmental_morphology/manuscript_v2.md").read_text()
    for value in [f"{summary['primary_n']:,}",f"{summary['event_n']:,}",f"{summary['ge7_n']:,}",
                  f"{summary['ge7_distance']:.3f}",f"{summary['shuffle_front_observed']:.3f}",
                  f"{summary['vpd_region_delta']:.4f}"]:
        assert value in source,value
    assert "after duration, count, area, region, month and year adjustment" in source
    assert "mean-centered" in source.lower() and "Axis sign conventions are local" in source
    for forbidden in ["Authors and affiliations: to be confirmed","achieved median held-out","explains morphology deterministically"]:
        assert forbidden not in source
    # Generated publication manifest must match current bytes; no silent stale figures.
    publication=json.loads((ROOT/"analysis/v2/publication_manifest.json").read_text())
    for path,digest in publication["artifacts"].items():assert sha256(ROOT/path)==digest,path
    for i in range(1,9):
        name=f"Figure_{i}" if i<=5 else f"Supplementary_Figure_{i-5}"
        for ext in ["pdf","png","svg"]:assert (ROOT/f"figures/v2/{name}.{ext}").stat().st_size>1000
        assert sha256(ROOT/f"figures/v2/{name}.png")==sha256(ROOT/f"docs/assets/figures/v2/{name}.png")
    return {**result,"claim_matrix":"pass","null_conservation":"pass","manuscript_table_numbers":"pass",
            "publication_hashes":"pass","web_figure_copies":"pass","main_figures":5,"supplementary_figures":3}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot",type=Path)
    parser.add_argument("--compare",type=Path)
    args=parser.parse_args();result=verify();current=fingerprints()
    if args.snapshot:args.snapshot.write_text(json.dumps(current,indent=2));result["snapshot_files"]=len(current)
    if args.compare:
        previous=json.loads(args.compare.read_text())
        changed=[p for p,v in previous.items() if current.get(p)!=v]
        added=sorted(set(current)-set(previous))
        result.update(deterministic_regeneration="pass" if not changed and not added else "fail",
            compared_files=len(previous),changed_files=changed,added_files=added)
    if args.compare or not (OUT/"reproducibility.json").exists():
        (OUT/"reproducibility.json").write_text(json.dumps(result,indent=2))
    inputs=json.loads((OUT/"validation_manifest.json").read_text())
    for path,digest in inputs["inputs"].items():assert sha256(ROOT/path)==digest,path
    paths=[ROOT/"scripts/validate_fire_vase_science.py",ROOT/"scripts/finalize_fire_vase_science.py",Path(__file__),
        ROOT/"scripts/fire_vase_v2.py",ROOT/"scripts/fire_vase_v2_manuscript.py",ROOT/"scripts/figures/make_figures_v2.py",
        ROOT/"src/cubedynamics/analysis_v2.py",ROOT/"config/analysis_v2.json",ROOT/"manuscript_figures/_figure_runner.py",
        ROOT/"scripts/figures/style.py"]
    manifest=dict(repository_sha=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        code_hashes={str(p.relative_to(ROOT)):sha256(p) for p in paths},artifacts=current,
        validation_input_manifest_sha256=sha256(OUT/"validation_manifest.json"),
        publication_manifest_sha256=sha256(ROOT/"analysis/v2/publication_manifest.json"),
        reference_manuscript=dict(path="docs/manuscripts/fire_vase_developmental_morphology/main-16.pdf",
            sha256="6d07ab1763a8e92d4584a49ea3123ab165c1f5d9c3ad8fc43e732ad2e28d1e31",use="user-supplied guidance; original unchanged"))
    manifest["verification_records"]={p.name:sha256(p) for p in [OUT/"statistical_reproduction.json",OUT/"quality_checks.json"] if p.exists()}
    (OUT/"freeze_manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps(result,indent=2))
    if result.get("deterministic_regeneration")=="fail":raise SystemExit(1)


if __name__=="__main__":main()
