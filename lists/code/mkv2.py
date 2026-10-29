# Verdicts for packet2 (read by Claude in the parent session, 2026-10-20 ~14:35 ET). Index = line in packet2_*.jsonl.
import json, sys
SP = sys.argv[1]
P = {0: ("CONFIRM", "Insulin sensitivity benefit of PGC-1a attributed to the paper."), 1: ("CONFIRM", "Restates the title finding."),
     2: ("CONFIRM", "Mitochondrial biogenesis preserves muscle mass, cited to the paper."), 3: ("CONFIRM", "LC3-II up-regulation in a sarcopenia model, cited as a finding."),
     4: ("CONFIRM", "PPARGC1A overexpression mitigates sarcopenia."), 5: ("CONFIRM", "Wenz et al. showed overexpression prevented atrophy and extended life span."),
     6: ("REJECT_OTHER", "Adipocyte dysfunction / NF-kB claim the paper does not make; likely mislinked."), 7: ("CONFIRM", "PGC1-a signalling prevents sarcopenia."),
     8: ("REJECT_OTHER", "IGF-1/PI3K claim; likely mislinked."), 9: ("CONFIRM", "Age-dependent PGC-1a decline cited to the paper."),
     10: ("CONFIRM", "Upregulation attenuates mitochondrial dysfunction and sarcopenia."), 11: ("CONFIRM", "Overexpression lowered IL-6/TNF-a."),
     12: ("CONFIRM", "Overexpression in old mice prevented atrophy and insulin resistance."), 13: ("CONFIRM", "Higher PGC1a in old mice: less oxidative stress, inflammation."),
     14: ("CONFIRM", "Transgenic mice: longer life, resistance to obesity and diabetes.")}
A = {0: ("CONFIRM", 0, "Tregs convert to Th17 cells, cited as fact."), 1: ("REJECT_OTHER", 1, "Silymarin bioavailability claim; not the hTERT paper's finding, likely mislinked."),
     2: ("CONFIRM", 1, "HOTAIR/miR-148b-3p/USF1 BTB finding in text and table."), 3: ("CONFIRM", 1, "Table row lists the finding."),
     4: ("REJECT_OTHER", 1, "NEAT1 row; cites a CCAT2 paper, mislinked."), 5: ("CONFIRM", 1, "HOTAIR/miR-20a-5p/HMGA2 finding."),
     6: ("CONFIRM", 1, "Table rows restate the daidzein SKOV3 results."), 7: ("CONFIRM", 1, "HOTAIR/HMGB1 spinal cord injury finding."), 8: ("CONFIRM", 1, "Same finding."),
     9: ("CONFIRM", 1, "Table row restates psoralidin results."), 10: ("REJECT_PASSING", 0, "One of a list of activity references."),
     11: ("CONFIRM", 1, "Luteolin neuroprotection finding, text and table."), 12: ("CONFIRM", 1, "Biochanin A melanoma finding."), 13: ("CONFIRM", 1, "Daidzein table row."),
     14: ("REJECT_PASSING", 1, "General statement of pharmacological potential."), 15: ("REJECT_OTHER", 0, "Comparison-table row of image counts."),
     16: ("CONFIRM", 0, "Acupressure improved sleep in dialysis patients."), 17: ("CONFIRM", 0, "Same finding."), 18: ("CONFIRM", 1, "PTEN inactivation hyperactivates mTOR, cited to the paper."),
     19: ("CONFIRM", 1, "WalK/WalR as the key regulator, cited as finding."), 20: ("REJECT_PASSING", 0, "Names a compound with a reference."),
     21: ("REJECT_OTHER", 1, "circTPCN/miR-634 claim; cites a miR-214 paper, mislinked."), 22: ("CONFIRM", 1, "Parthenolide thyroid results in text and table."),
     23: ("CONFIRM", 1, "Gut toxin and butyrate claims cited to the paper."), 24: ("CONFIRM", 1, "Bcl-2/HMGA2 feedback finding."), 25: ("CONFIRM", 1, "Rituximab PI3K/AKT table row."),
     26: ("CONFIRM", 1, "Galectin-3 from CSCs triggers T-cell apoptosis."), 27: ("CONFIRM", 1, "Cell-based vaccine finding used to support CAR-T argument."),
     28: ("CONFIRM", 0, "miR-302a inhibits BC invasiveness, as prior evidence."), 29: ("CONFIRM", 0, "Sorafenib + cisplatin results, 'consistent with our results'."),
     30: ("CONFIRM", 0, "PTEN activation under HG, cited as a demonstration."), 31: ("CONFIRM", 0, "miR-31 acts as tumour suppressor in breast cancer."),
     32: ("CONFIRM", 1, "Marathon raised SIRT1 expression."), 33: ("CONFIRM", 0, "Nassirpour et al. found high miR-221 in TNBC."),
     34: ("CONFIRM", 0, "'In our previous study we found...': the authors' own retracted result."), 35: ("CONFIRM", 1, "Chrysanthemum stroke trial results in text and table."),
     36: ("CONFIRM", 0, "'Strong evidence' for celecoxib + EGFR-TKI."), 37: ("CONFIRM", 1, "Dll4 expression in malignant cells."),
     38: ("CONFIRM", 0, "Uses the paper's 71 DEGs to build a model."), 39: ("CONFIRM", 1, "Table row restates miR-32-5p finding."), 40: ("CONFIRM", 1, "miR-665 HCC finding."),
     41: ("CONFIRM", 0, "Zhao and colleagues found four HCM biomarkers."), 42: ("CONFIRM", 1, "Table row: piperlongumine apoptosis."),
     43: ("REJECT_PASSING", 0, "One of a list of activity references."), 44: ("CONFIRM", 0, "Antioxidant mechanism (GSH, TBARS) cited to the paper."),
     45: ("CONFIRM", 1, "Table row restates the daidzein SKOV3 results."), 46: ("REJECT_OTHER", 1, "SARS-CoV-2 / vitamin D observational claims; mislinked."),
     47: ("CONFIRM", 1, "Table row miR-421 finding."), 48: ("REJECT_PASSING", 0, "Credits the paper with naming visfatin only."),
     49: ("REJECT_PASSING", 0, "Credits the paper with identifying visfatin only."), 50: ("CONFIRM", 0, "Does not compete with insulin for the receptor."),
     51: ("CONFIRM", 1, "Insulin-mimetic effects 'proven' by the paper."), 52: ("CONFIRM", 0, "Fukuhara et al. demonstrated INSR activation (debate noted, retraction not)."),
     53: ("REJECT_PASSING", 0, "Credits the paper with identifying visfatin only.")}
for kind, V in (("papers", P), ("authors", A)):
    rows = [json.loads(l) for l in open(f"{SP}/packet2_{kind}.jsonl")]
    assert len(rows) == len(V), (kind, len(rows), len(V))
    with open(f"{SP}/verdicts2_{kind}.jsonl", "w") as f:
        for i, r in enumerate(rows):
            v = V[i]
            out = {"pair_id": r["pair_id"], "group": r["group"], "verdict": v[0]}
            if kind == "authors": out["review"] = bool(v[1])
            out["reason"] = v[-1]
            f.write(json.dumps(out) + "\n")
    print(kind, len(rows))
