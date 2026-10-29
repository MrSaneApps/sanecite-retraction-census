"""Applies the 21 Oct 2026 rulings to list_corrections.json: the Suresh exception switched off, and citations of
works retracted for reasons that do not touch the results left out, from the notice wording."""
import json, os

P = os.path.expanduser("site/data/phase2/list_corrections.json")
C = json.load(open(P))
DAY = "2026-10-21"
C["left_off_kept"]["enabled"] = False
C["left_off_kept"]["reason"] = ("Switched off 21 Oct 2026: the paper is removed from the left-off table. With the notice date it falls "
                                "below the cut, and its notice cites duplicated text only.")
C["checks_exclude"] = []  # the two sample readings are now covered by excluded_works
C["excluded_works_rule"] = (
    "Citations of a work are left out when its retraction notice gives only reasons that do not touch the results: author "
    "withdrawal with a stated non-results reason, ethics paperwork, redundant or duplicate publication of a result that stays "
    "published, plagiarism or reuse of text only, copyright or software-licence changes, a wrong journal, or forged or disputed "
    "authorship. Figure or image duplication or reuse, data problems, errors, fabrication, paper mills and compromised peer review "
    "still count. A notice with no stated reason, or an unclear one, still counts and is marked reason unclear. Applied where we "
    "have read the notice.")
X = {  # pmid: (notice pmid, what the notice says)
    "21772732": ("37305772", "text overlapping an earlier article: \"owing to duplicity of text, the article is being retracted\""),
    "24711954": ("30993018", "85% of the text taken from earlier publications, mostly without citation"),
    "32286091": ("33095058", "duplicate publication of Psychiatry Research 2020 and Asian Journal of Psychiatry 2020 papers"),
    "16807438": ("22024726", "redundant publication of a trial that stays published in J Clin Oncol 2005"),
    "20068105": ("25934892", "duplicate or redundant publication: identical text in an article published at the same time in Mol Cancer Ther"),
    "29273065": ("", "the welfare of the mice; ethics approval of the tumour volumes and humane endpoints could not be confirmed"),
    "30080301": ("30080301", "withdrawn because \"the authors have not provided a signed Copyright Transfer Agreement\""),
    "15222900": ("", "the author changed the software licence, breaching the journal's software availability policy"),
    "29445078": ("", "\"mistakenly submitted and processed the publication in the wrong journal\""),
    "22912826": ("29097821", "duplicate publication of data reported in the authors' Int J Mol Sci 2012 article"),
    "28260102": ("30226621", "written on the template of an earlier article; \"all the data reported in our study were original\""),
    "29316313": ("33686796", "submitted \"without consent in any form by the named co-authors\""),
    "22621620": ("24772487", "an unresolved authorship claim by an unlisted author"),
    "30385776": ("30918283", "submitted \"without the knowledge or consent of the other listed author\""),
    "19607689": ("19818140", "previously published in Acupuncture and Electro-therapies Research"),
    "32647692": ("36330398", "a co-author objected to publication"),
    "25336793": ("25810581", "names of authors who never contributed were included"),
    "19371446": ("", "the study had no ethics committee approval"),
    "27183876": ("", "the authors could not document ethics committee approval"),
}
works = json.load(open(os.path.expanduser("work/listfix/author_works.json")))
notice = {w["cited"]: w["notice"] for w in works}
C["excluded_works"] = {p: {"notice_pmid": n or notice.get(p, ""), "notice_says": why, "date": DAY} for p, (n, why) in X.items()}
RC = C["reason_class"]
for p in ("16807438", "20068105", "29273065", "30080301"):
    RC[p].update({"class": "not the results", "why": X[p][1]})
RC["31114273"].update({"class": "results", "why": "text similarity with the authors' own article and image manipulation in Figures 1 and 2"})
for p in ("27416558", "30372802", "30551524", "31559899", "31838274", "31933941", "32006899", "32716637", "33347877", "33450262",
          "34186282", "35033815"):
    RC[p].update({"class": "results", "why": "the notice names a problem with the data, images or results"})
for p in ("31081079", "31322140", "32283217"):
    RC[p]["class"] = "unclear"
C["reason_class_source"] = "Notice text from PubMed, Europe PMC, PMC and publisher pages, read by hand 21 Oct 2026."
F = {f["path"]: f for f in C["fields"]}
NEW = {
    "15604363": ('An Osaka University research integrity committee examined the insulin-receptor experiments and the university recommended '
                 'retraction; the authors "continue to stand by our conclusions" but found "not all preparations of visfatin bind to and '
                 'activate the insulin receptor"', "notice PMID 17962537, doi:10.1126/science.318.5850.565b, read in full on science.org"),
    "30193239": ('A University of Manchester panel "found no evidence of intentional fabrication" but, because of flaws in the review '
                 'process, "cannot confirm that the results of the meta-analysis are wholly valid"',
                 "notice PMID 32421149, doi:10.1001/jamainternmed.2020.1755, read in full on jamanetwork.com"),
    "15833829": ('The authors could not reproduce some of the reported transformation events and "suspect the phenomenon is due to a '
                 'cross-contamination artifact"; five of the seven authors agreed to the retraction',
                 "notice PMID 20710046, doi:10.1158/0008-5472.CAN-10-2451, read in full on aacrjournals.org"),
    "32286091": ('The paper is "substantively similar to two previously published papers and therefore constitutes duplicate publication"',
                 "notice PMID 33095058, doi:10.1080/13548506.2020.1833631, read in full on tandfonline.com"),
}
for pmid, (reason, src) in NEW.items():
    F[f"papers/{pmid}/reason"]["new"] = reason
    F[f"papers/{pmid}/reason"]["source"] = src
    F[f"papers/{pmid}/reason"]["reason"] = "Printed reason must be the notice's own wording, never the Retraction Watch group."
    F[f"papers/{pmid}/reason_source"]["new"] = src
    F[f"papers/{pmid}/reason_source"]["source"] = src
k = "papers/19772305/reason_source"
F[k]["new"] = F[k]["source"] = ("notice PMID 22901075, doi:10.1021/nn302965w. The ACS page shows the notice only to subscribers; "
                                "PubMed, PMC, Europe PMC and Crossref hold no text. Not yet read first-hand.")
C["fields"] = list(F.values())
json.dump(C, open(P, "w"), indent=1, ensure_ascii=False)
print("excluded works", len(C["excluded_works"]), {c: sum(v["class"] == c for v in RC.values()) for c in ("results", "not the results", "unclear")})
