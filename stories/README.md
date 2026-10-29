# Stories: the re-analyses behind sanecite.com/stories

Code and data for the case stories published on sanecite.com/stories on 29 October 2026. Staged by
`scripts/stage_release.py` on 2026-10-29. The papers' full texts and figures we read are not included; each story links them.

| Path | What it is |
|---|---|
| `meta.py` | Small meta-analysis helpers matching RevMan: Mantel-Haenszel fixed and DerSimonian-Laird random risk ratios, inverse-variance mean differences |
| `vitc/rerun.py` | The sepsis guideline story: re-runs the vitamin C meta-analyses with and without the retracted trial (risk ratios for mortality; Hedges' g with DerSimonian-Laird random effects for the vasoactive-drug outcome) |
| `syn/rerun_sildenafil.py`, `syn/rerun_dhea.py` | Re-runs of two reviews' pooled estimates with and without the retracted trial (BMC Pediatrics 2024, sildenafil; J Ovarian Res 2025, DHEA) |
| `ctgov_sweep.py` | Searches ClinicalTrials.gov for registered trials that cite a retracted paper in the census |
| `ctgov_hits.jsonl` | Everything the sweep found: 646 pairs of a registered trial and a retracted paper it lists |
| `ctgov_after.json` | The 224 pairs from `ctgov_hits.jsonl` where the trial was first submitted after the retraction, leaving out retract-and-replace notices |

Each script prints its numbers; run it with Python 3 from this folder (`ctgov_sweep.py` expects the census
`data/stage1_papers.jsonl` one folder up and calls the ClinicalTrials.gov API).
