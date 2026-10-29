"""Adds the printed-reason and display-year corrections to list_corrections.json "fields" (replacing earlier copies)."""
import json, os

P = os.path.expanduser("site/data/phase2/list_corrections.json")
C = json.load(open(P))
DAY = "2026-10-21"
RW = "error or unreliable results"
BUNDLE = "misconduct, fabrication or duplication"
NOT_READ = "Publisher page blocks scripted access (403) and PubMed, PMC, Europe PMC and Crossref hold no notice text; not yet read first-hand."
R = [  # pmid, old reason, new reason ("" = not yet read), source
    ("15604363", RW, "", "notice PMID 17962537, doi:10.1126/science.318.5850.565b. " + NOT_READ),
    ("32356626", RW, 'The authors could not get the raw data audited, so they were "unable to validate the primary data sources"',
     "notice PMID 32501665 (PMC7274164), read in full"),
    ("18453793", RW, 'An independent statistical review found the results "misleading due to issues regarding the sensitivity and specificity" of the adherence measure',
     "notice PMID 37594022 (PMC10497024), read in full"),
    ("30193239", RW, "", "notice PMID 32421149, doi:10.1001/jamainternmed.2020.1755. " + NOT_READ),
    ("17715156", BUNDLE, 'The authors retracted it over "the misuse and re-use of western blot bands" in Figures 3 and 4A, which broke the journal\'s editorial policy',
     "notice PMID 21914820, doi:10.1242/jcs.098830; text read from the OpenAlex copy of the journal's notice page (journal page 403)"),
    ("19772305", BUNDLE, "", "notice PMID 22901075, doi:10.1021/nn302965w. " + NOT_READ),
    ("32450107", RW, 'Independent reviewers could not get the full Surgisphere dataset, so the authors "can no longer vouch for the veracity of the primary data sources"',
     "notice PMID 32511943 (PMC7274621), read in full"),
    ("28368401", RW, 'The authors found "serious errors in Figs. 5c and 7b, resulting from the data collection process" and are no longer confident in the conclusions',
     "notice PMID 31197212 (PMC6755959), read in full"),
    ("15833829", RW, "", "notice PMID 20710046, doi:10.1158/0008-5472.CAN-10-2451. " + NOT_READ),
    ("21753854", RW, 'Problems with Fig. 1d and Supplementary Fig. 31b, and missing original data, "raise concerns regarding the integrity of the figures"; five authors disagree with the retraction',
     "notice PMID 30046103 (PMC6148382), PubMed abstract"),
    ("19918075", BUNDLE, 'A University of Cologne investigation "concluded that there was scientific misconduct": blots in Figs. 2D and 3B also appear in an unrelated paper, and a tubulin blot is duplicated',
     "notice PMID 27994157 (PMC5206512), read in full on PMC"),
    ("12609035", BUNDLE, 'Image duplications in Figure 3b and in loading-control lanes of Figures 2g, 3a, 4e and 4f; the authors "accept that integrity of the scientific literature is compromised by the data manipulation"',
     "notice PMID 27170951, doi:10.1111/tpj.13066, PubMed abstract"),
    ("21772732", BUNDLE, 'The text overlaps an earlier article in another journal: "owing to duplicity of text, the article is being retracted"',
     "notice PMID 37305772 (PMC10256947), read in full"),
    ("24711954", "Material from earlier publications used mostly without citation (the notice puts it at 85% of the text)",
     "Material from earlier publications used mostly without citation (the notice puts it at 85% of the text)",
     "notice PMID 30993018 (PMC6434292), read in full (correction dae55f0)"),
    ("32286091", BUNDLE, "", "notice PMID 33095058, doi:10.1080/13548506.2020.1833631. " + NOT_READ),
    ("35480139", BUNDLE, 'The publisher found "evidence of systematic manipulation of the publication and peer-review process" and cannot "vouch for the reliability or integrity" of the article',
     "notice PMID 38188754 (PMC10769770), read in full"),
]
F = []
for pmid, old, new, src in R:
    why = "Printed reason must be the notice's own wording, never the Retraction Watch group (Gate 2, Gate 14)."
    if not new:
        why += " Not yet read, so no reason is printed."
    if old != new:
        F.append({"path": f"papers/{pmid}/reason", "old": old, "new": new, "source": src, "date": DAY, "reason": why})
    F.append({"path": f"papers/{pmid}/reason_source", "old": None, "new": src, "source": src, "date": DAY,
              "reason": "Every printed reason names its notice."})
F.append({"path": "papers/21772732/retraction_year", "old": "2017", "new": "2023", "source": "notice PMID 37305772",
          "date": DAY, "reason": "The 2017 date was a Retraction Watch placeholder; correction sent 21 Oct."})
F += [
    {"path": "cited/29036788/retraction_year", "old": "2022", "new": "2023 (notice online 11 Dec 2022)",
     "source": "PubMed 36502305: issue 2023;36(1); entered PubMed 11 Dec 2022", "date": DAY,
     "reason": "Nabavi reply of 21 Oct gave 2023, the notice's issue year. The census window keeps 2022, the online year (Gate 15)."},
    {"path": "cited/30080301/retraction_year", "old": "", "new": "retraction date unknown (Retraction Watch estimate)",
     "source": "Retraction Watch record: date unknown, estimated from notifications; PubMed has no notice", "date": DAY,
     "reason": "The letters printed 2019; Gate 1 rejects dates the source itself flags as unknown."},
    {"path": "cited/30080301/first_author", "old": "", "new": "Wu L", "source": "PubMed 30080301", "date": DAY,
     "reason": "Europe PMC returns no author list for the replaced record."},
]
paths = {f["path"] for f in F}
C["fields"] = [f for f in C.get("fields", []) if f["path"] not in paths] + F
json.dump(C, open(P, "w"), indent=1, ensure_ascii=False)
print("fields", len(C["fields"]))
