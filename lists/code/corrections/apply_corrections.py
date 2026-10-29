#!/usr/bin/env python3
"""Adds the 22 Oct 2026 corrections to data/phase2/list_corrections.json. Boundary lists are computed from the
Europe PMC first-publication dates in citing_fpd.json against each notice's first online date, then printed for
review. Idempotent: an entry already present is replaced, not duplicated."""
import csv, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.expanduser("site")
PATH = f"{REPO}/data/phase2/list_corrections.json"
F = json.load(open(PATH))
FPD = json.load(open(f"{HERE}/citing_fpd.json"))
# Europe PMC gives a 1 Jan placeholder for this one; the PMC XML epub date is the first online date
FPD["PMC10074620"] = {"fpd": "2023-04-03"}
ROWS = list(csv.DictReader(open(f"{REPO}/data/phase2/citations.csv")))
DAY = "2026-10-22"
LS_SRC = "citing papers of {y} sorted by Europe PMC first publication date; boundary papers checked against PMC XML epub dates (PMC10074620: Europe PMC has a 1 Jan placeholder, PMC XML epub 2023-04-03)"

# (pmid, old, new, notice pmid, notice online, PubMed citation of the notice, notice doi, label, extra)
DATES = [
    ("33577844", "2021", "2023", "36804892", "2023-02-18", "Life Sci 2023 Apr 15;319, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121426", "Chen W et al., Life Sci 273 (2021) 119184",
     "; ScienceDirect notice read 22 Oct 2026: Western blots found unreliable and the authors could not supply the raw data"),
    ("33347877", "2021", "2023", "36804891", "2023-02-18", "Life Sci 2023 Apr 1;318, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121422", "Mao R et al., Life Sci 268 (2021) 118937", ""),
    ("33450262", "2021", "2023", "36804890", "2023-02-18", "Life Sci 2023 Apr 1;318, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121423", "Li H et al., Life Sci 269 (2021) 119017", ""),
    ("33316267", "2021", "2023", "36804901", "2023-02-18", "Life Sci 2023 Apr 1;318, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121421", "Liao H et al., Life Sci 267 (2021) 118893", ""),
    ("33232688", "2020", "2023", "36804895", "2023-02-18", "Life Sci 2023 Apr 1;318, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121420", "Life Sci 266 (2021) 118794", ""),
    ("33482187", "2021", "2023", "36804893", "2023-02-18", "Life Sci 2023 Apr 1;318, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121424", "Life Sci 270 (2021) 119072", ""),
    ("33513398", "2021", "2023", "36804902", "2023-02-18", "Life Sci 2023 Apr 15;319, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121425", "Life Sci 271 (2021) 119111", ""),
    ("33617858", "2021", "2023", "36804898", "2023-02-18", "Life Sci 2023 Apr 15;319, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121428", "Life Sci 277 (2021) 119225", ""),
    ("33652034", "2021", "2023", "36804900", "2023-02-18", "Life Sci 2023 Apr 15;319, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121427", "Life Sci 274 (2021) 119249", ""),
    ("33872661", "2021", "2023", "36804903", "2023-02-18", "Life Sci 2023 Apr 15;319, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121429", "Life Sci 278 (2021) 119495", ""),
    ("34089727", "2021", "2023", "36804899", "2023-02-18", "Life Sci 2023 Apr 15;319, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121430", "Life Sci 279 (2021) 119670", ""),
    ("36007610", "2022", "2023", "36804897", "2023-02-18", "Life Sci 2023 Apr 15;319, Epub 2023 Feb 18", "10.1016/j.lfs.2023.121431", "Life Sci 307 (2022) 120906", ""),
    ("33781831", "2021", "2023", "37179191", "2023-05-11", "Life Sci 2023 Jul 15;325, Epub 2023 May 11", "10.1016/j.lfs.2023.121731", "Life Sci 277 (2021) 119408", ""),
    ("34274310", "2021", "2022", "35835620", "2022-07-11", "Life Sci 2022 Sep 15;305, Epub 2022 Jul 11", "10.1016/j.lfs.2022.120749", "Life Sci 282 (2021) 119825", ""),
    ("19015639", "2008", "2011", "22011759", "2011-10-20", "Oncogene 2011 Oct 20;30(42):4374", "10.1038/onc.2011.388", "Zhang B et al., Oncogene 2009", ""),
    ("24001238", "2014", "2013", "24829954", "2013-10-28", "Br J Nutr 2014 May (print)", "10.1017/s0007114513003656", "Lin CH et al., Br J Nutr 2013", ""),
]
LIFESCI = ("The census year was the article's own issue year, from the publisher's same-DOI Crossref retraction record (Elsevier stamps it "
           "with the issue date); the only notice is the one above. Same class as Ling (register P3).")
REASONS = {
    "34274310": LIFESCI.replace("Same class as Ling (register P3).", "Same class as Ling (register P3), found in the 22 Oct sweep of every Life Sci work."),
    "33781831": LIFESCI.replace("Same class as Ling (register P3).", "Same class as Ling (register P3), found in the 22 Oct sweep of every Life Sci work."),
    "19015639": ("The 2008 year was the Retraction Watch date; the notice is dated 20 Oct 2011. Citations from 2010, among them the PLOS ONE "
                 "sample PMC2942851 (online 20 Sep 2010, PMC XML and Europe PMC), were made before the retraction (Gate 15). The first "
                 "PLOS ONE letter listed that citation; the 27 Oct follow-up removes it."),
    "24001238": ("The 2014 year is the notice's print issue (May 2014); the notice went online 28 Oct 2013 (Crossref). Every citing paper "
                 "is from 2015 or later, so no citation changes; the year printed beside Huang CY's item changes."),
}
by = {}
for r in ROWS: by.setdefault(r["retracted_pmid"], []).append(r)
new_dates = []
for pmid, old, new, npm, on, cite, ndoi, label, extra in DATES:
    keep, drop = [], []
    for r in by[pmid]:
        assert r["retraction_year"] == old, (pmid, r["retraction_year"])
        if r["citing_year"] != new: continue
        f = FPD[r["citing_pmcid"]]["fpd"]
        (keep if f > on else drop).append(r["citing_pmcid"])
    late = [r["citing_pmcid"] for r in by[pmid] if int(r["citing_year"]) > int(new) and FPD[r["citing_pmcid"]]["fpd"] <= on]
    assert not late, (pmid, late)  # a later-year paper online before the notice would need its own exclusion
    print(pmid, old, "->", new, "keep", keep, "drop", drop)
    src = (f"PubMed {npm} ({cite}), RetractionIn link on PubMed {pmid}; Crossref doi:{ndoi} " +
           (f"online {on}" if pmid in ("19015639", "24001238") else f"registered {on}") + extra + "; " + LS_SRC.format(y=new))
    new_dates.append({"retracted_pmid": pmid, "field": "retraction_year", "old": old, "new": new, "notice_pmid": npm,
                      "notice_online": on, "boundary_keep": keep, "boundary_drop": drop, "source": src, "date": DAY,
                      "reason": f"{label}: " + REASONS.get(pmid, LIFESCI)})
F["retraction_dates"] = [d for d in F["retraction_dates"] if d["retracted_pmid"] not in {x["retracted_pmid"] for x in new_dates}] + new_dates

EXC = [  # citing paper, pair, first online, {pmid: notice}, notice source
    ("PMC10841002", "32765702", "2021-11-16", "2022-08-09 (notice PMID 36160892)", "PubMed 36160892 Epub 2022-08-09; Crossref doi:10.3892/etm.2022.11557 online 2022-08-09",
     "Bioengineered sample: published online before the work it cites (Pan Y et al., Exp Ther Med) was retracted. The first Bioengineered letter listed it."),
    ("PMC7836849", "32356626", "2020-06-03", "2020-06-04 (notice PMID 32501665)", "PubMed 32501665 Epub 2020-06-04; Crossref registered 2020-06-04",
     "Published online the day before the Mehra NEJM retraction; one support citation (red team 21 Oct, class 2a)."),
    ("PMC3555345", "19772305", "2012-07-20", "2012-08-20 (notice PMID 22901075)", "PubMed 22901075 Epub 2012-08-20; Crossref online 2012-08-20",
     "Published online a month before the Khodakovskaya retraction; one support citation (red team 21 Oct, class 2a)."),
    ("PMC4762519", "12609035", "2015-11-06", "2015-11-13 (notice PMID 27170951)", "Crossref doi of notice PMID 27170951 published online 2015-11-13 (PubMed entry May 2016)",
     "Published online a week before the Voinnet retraction; one support citation, found in the 22 Oct Gate 15 sweep of every listed paper."),
    ("PMC3918054", "15833829", "2010-07-13", "2010-08-14 (notice PMID 20710046)", "PubMed 20710046 (Cancer Res 2010 Aug 15); Crossref online 2010-08-14",
     "Published online before the Rubio retraction; a passing mention, found in the 22 Oct Gate 15 sweep of every listed paper."),
    ("PMC5377414", "19918075", "2016-10-08", "2016-12-19 (notice PMID 27994157)", "PubMed 27994157 Epub 2016-12-19; Crossref online 2016-12-19",
     "Published online before the Wenz retraction; a passing mention, found in the 22 Oct Gate 15 sweep of every listed paper."),
]
ex = []
for pmc, pmid, on, ret, nsrc, why in EXC:
    assert FPD[pmc]["fpd"] == on, (pmc, FPD[pmc])
    ex.append({"citing_pmcid": pmc, "pairs": [f"{pmid}>{pmc}"], "first_online": on, "retracted": {pmid: ret},
               "source": f"PMC XML epub {on} and Europe PMC firstPublicationDate; {nsrc}", "date": DAY, "reason": why})
F["exclude_citing"] = [x for x in F["exclude_citing"] if x["citing_pmcid"] not in {e["citing_pmcid"] for e in ex}] + ex

CITED = [
    ("cited/33347877/retraction_year", "2021", "2023", "notice PMID 36804891, Epub 2023 Feb 18"),
    ("cited/33450262/retraction_year", "2021", "2023", "notice PMID 36804890, Epub 2023 Feb 18"),
    ("cited/24001238/retraction_year", "2014", "2013", "notice PMID 24829954, doi:10.1017/s0007114513003656, Crossref online 2013-10-28"),
]
paths = {c[0] for c in CITED}
F["fields"] = [f for f in F["fields"] if f["path"] not in paths] + [
    {"path": p, "old": o, "new": n, "source": s, "date": DAY, "reason": "The year beside the author item must be the notice's online year (Gate 1)."}
    for p, o, n, s in CITED]

TL_SRC = "Received, accepted and first online dates from the PMC XML (read 22 Oct 2026); retraction dates from the PubMed notice and Crossref"
MOG = "Dates of first submission are the author's own account, in his reply of 21 Oct 2026; the rest from the PMC XML (read 22 Oct 2026) and the PubMed notices"
TL = [
    ("PMC10209650", "33347877", "Submitted 13 Feb 2023, before the retraction of 18 Feb 2023; accepted (7 May 2023) and published (9 May 2023) after it.", TL_SRC),
    ("PMC10333929", "33450262", "Submitted 12 Dec 2022, before the retraction of 18 Feb 2023; accepted (16 Jun 2023) and published (27 Jun 2023) after it.", TL_SRC),
    ("PMC8182944", "31378887", "First submitted in Mar 2019, the author says, before the retraction (November 2020); received by this journal 20 Feb 2021, accepted (24 May 2021) and published (7 Jun 2021) after it.", MOG),
    ("PMC8832734", "16510599", "First submitted in Jul 2018, the author says, before the retraction (September 2018); received by this journal 13 Nov 2021, accepted (30 Jan 2022) and published (10 Feb 2022) after it.", MOG),
    ("PMC8976361", "31114273", "First submitted in May 2019, the author says, before the retraction (July 2019); received by this journal 22 Dec 2021, accepted (23 Mar 2022) and published (2 Apr 2022) after it.", MOG),
    ("PMC9167543", "", "First submitted in Mar 2021, the author says, before the five retractions (May to October 2021); received by this journal 4 Jan 2022, accepted (7 May 2022) and published (4 Jun 2022) after them.", MOG),
    ("PMC9808980", "31378902", "Submitted 17 Nov 2021, before the retraction (September 2022); accepted (29 Dec 2022) and published (3 Jan 2023) after it.", TL_SRC),
    ("PMC11079401", "28586066", "First submitted in Jan 2023, the author says, before the retraction (February 2023); received by this journal 26 Feb 2024, accepted (30 Apr 2024) and published (1 May 2024) after it.", MOG),
]
keys = {(c, r) for c, r, _, _ in TL}
F["timelines"] = [t for t in F["timelines"] if (t["citing_pmcid"], t["retracted_pmid"]) not in keys] + [
    {"citing_pmcid": c, "retracted_pmid": r, "text": t, "source": s, "date": DAY} for c, r, t, s in TL]

F["check_notes"] = [{
    "list": "paper", "entry": "32450107", "pair_id": "32450107>PMC7524676",
    "old": "The next sentences (outside the census window) call the paper fraudulent and say it was retracted.",
    "new": "The next sentences (outside the census window) say the paper was retracted and question its data; the notice says the authors \"can no longer vouch for the veracity of the primary data sources\".",
    "source": "notice PMID 32511943 (PMC7274621)", "date": DAY,
    "reason": "A reading note never calls work fraud; it quotes the notice instead."}]
F["made"] = DAY
s = json.dumps(F, indent=1, ensure_ascii=False)
open(PATH, "w").write(s)
print("written", len(s))
