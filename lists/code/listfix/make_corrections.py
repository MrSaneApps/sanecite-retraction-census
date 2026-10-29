"""Writes data/phase2/list_corrections.json (everything except the "fields" list, which is kept from the existing
file). Facts come from the 21 Oct 2026 red team, the notices read in listfix-20261021/, and the sent corrections."""
import json, os

H = os.path.expanduser("~")
SITE = f"{H}/site/data/phase2"
FIX = f"{H}/work/sanecite-top10-20261020/listfix-20261021"
RT = f"{H}/work/sanecite-top10-20261020/redteam-20261021"
DAY = "2026-10-21"
RED = "REDTEAM_FROM_FEEDBACK_2026-10-21.md"
out_path = f"{SITE}/list_corrections.json"
old = json.load(open(out_path)) if os.path.exists(out_path) else {}

C = {
    "about": ("Every correction the Lists page applies on top of the generated data (lists.json, author_items.json, "
              "citations.csv, list_checks.csv). tools/lists.py applies them at build time, so a data regeneration cannot "
              "undo one silently: each entry names the value it expects to find and the build stops if the data holds "
              "neither that value nor the corrected one. Dates and reasons come from the retraction notices, never from "
              "the Retraction Watch database."),
    "made": DAY,
    # ---------------------------------------------------------------- citations: windows and exclusions
    "retraction_dates": [
        {"retracted_pmid": "21772732", "field": "retraction_year", "old": "2017", "new": "2023",
         "notice_pmid": "37305772", "notice_online": "2023-03-31",
         "boundary_keep": ["PMC10711914", "PMC11285609", "PMC10728710", "PMC10648101", "PMC10565121", "PMC10573726",
                           "PMC10555937", "PMC10477304", "PMC10370340", "PMC10403894", "PMC11406368", "PMC10406285",
                           "PMC10395843", "PMC10367231", "PMC10212178", "PMC10212150", "PMC10142171", "PMC10120026"],
         "boundary_drop": ["PMC10097130", "PMC10005739", "PMC10011792", "PMC10036898", "PMC9997887", "PMC9936663",
                           "PMC9972206", "PMC9915703", "PMC10041446", "PMC9379871"],
         "source": "PubMed 37305772 (J Hum Reprod Sci 2023 Jan-Mar;16(1):87); Crossref online 2023-03-31; "
                   "citing papers of 2023 sorted by Europe PMC first publication date (SURESH_CORRECTION_DERIVATION_2026-10-21.md)",
         "date": DAY, "reason": "The 2017 date was a Retraction Watch placeholder. Correction sent to the author on 21 Oct: 23 of 70."},
        {"retracted_pmid": "30121199", "field": "retraction_year", "old": "2018", "new": "2023",
         "notice_pmid": "37179192", "notice_online": "2023-05-11", "boundary_keep": ["PMC10363794"], "boundary_drop": [],
         "source": "PubMed 37179192 (Epub 2023 May 11); PMC10363794 first online 2023-05-29 (Europe PMC) "
                   "(WAVE3_DATE_RESOLUTION_2026-10-21.md)",
         "date": DAY, "reason": "The 2018 year echoed the paper's own online date in a Retraction Watch-sourced Crossref entry."},
        {"retracted_pmid": "32035086", "field": "retraction_year", "old": "2020", "new": "2023",
         "notice_pmid": "36821969", "notice_online": "2023-02-21", "boundary_keep": [], "boundary_drop": [],
         "source": "PubMed 36821969 (Epub 2023 Feb 21) (WAVE3_DATE_RESOLUTION_2026-10-21.md)",
         "date": DAY, "reason": "The 2020 year echoed the paper's own online date in a Retraction Watch-sourced Crossref entry."},
    ],
    "exclude_citing": [
        {"citing_pmcid": "PMC10278211", "pairs": ["25030358>PMC10278211", "28729638>PMC10278211"], "first_online": "2022-01-05",
         "retracted": {"25030358": "2022-10-23 (notice PMID 36273359)", "28729638": "2022 Jun (notice PMID 35701562)"},
         "source": "PMC XML epub 2022-01-05 and Europe PMC firstPublicationDate; Crossref publisher update; PubMed notices",
         "date": DAY, "reason": "Published online before both works it cites were retracted (Gate 15). Drops Baradaran B to 5 papers."},
        {"citing_pmcid": "PMC10761534", "pairs": ["31564894>PMC10761534", "34712356>PMC10761534"], "first_online": "2023-05-13",
         "retracted": {"31564894": "2023-07-31 (notice PMID 37546175)", "34712356": "2023-09-27 (notice PMID 37811266)"},
         "source": "PMC XML epub 2023-05-13 and Europe PMC firstPublicationDate; PubMed and Crossref notice dates",
         "date": DAY, "reason": "Published online before both works it cites were retracted (Gate 15)."},
    ],
    "checks_exclude": [
        {"list": "journal", "entry": "PLoS One", "pair_id": "15222900>PMC4963129",
         "source": RED + " class 3b", "date": DAY,
         "reason": "TREEFINDER was retracted when its author changed the software licence; the citation is for the tool, and no finding was retracted."},
        {"list": "journal", "entry": "Bioengineered", "pair_id": "29445078>PMC8291797",
         "source": RED + " class 3b; PubMed 29445078 (Med Sci Monit Basic Res, RetractionIn 2018;24:232)", "date": DAY,
         "reason": "The miR-144 paper was retracted because it was submitted to the wrong journal, not over its results."},
    ],
    "left_off_kept": {
        "enabled": True, "pmid": "21772732",
        "footnote": ("We first listed this paper with a retraction year of 2017, which was wrong. With the notice's date (2023) "
                     "it would not make the list on the count alone. We keep it in this table because we told the author we would."),
        "source": "Correction sent 21 Oct 2026 (paper-21772732-CORRECTION.txt)", "date": DAY,
        "reason": "Owner ruling pending: keep or remove. Set enabled to false to remove the exception, and the paper with it."},
    # ---------------------------------------------------------------- author items: notes printed beside an item
    "timelines": [
        {"citing_pmcid": "PMC10716031", "retracted_pmid": "34974791",
         "text": "Submitted 21 Sep 2023, before the retraction of 18 Oct 2023; revised, accepted and published (1 Dec 2023) after it."},
        {"citing_pmcid": "PMC10826439", "retracted_pmid": "31115031",
         "text": "Submitted 15 May 2023, before the retraction (July 2023); accepted and published (2 Dec 2023) after it."},
        {"citing_pmcid": "PMC8100681", "retracted_pmid": "27657824",
         "text": "Submitted 22 Sep 2020, before the retraction of 25 Nov 2020; accepted and published (22 Apr 2021) after it."},
        {"citing_pmcid": "PMC8862212", "retracted_pmid": "33958893",
         "text": "Submitted 9 Dec 2021, before the retraction of 23 Dec 2021; accepted and published (22 Feb 2022) after it."},
        {"citing_pmcid": "PMC8916230", "retracted_pmid": "32850336",
         "text": "Submitted 23 Jul 2021, before the retraction of 30 Dec 2021; accepted and published (25 Feb 2022) after it."},
        {"citing_pmcid": "PMC10902086", "retracted_pmid": "25311221",
         "text": "Submitted 2 Jul 2023, before the retraction of 11 Aug 2023; accepted and published (29 Feb 2024) after it."},
        {"citing_pmcid": "PMC9808980", "retracted_pmid": "31378902",
         "text": "Submitted 17 Nov 2021, before the retraction (September 2022); accepted and published (3 Jan 2023) after it."},
        {"citing_pmcid": "PMC10887337", "retracted_pmid": "34900185",
         "text": "Submitted 9 Aug 2023 and accepted 2 Oct 2023, both before the retraction of 6 Dec 2023; published (12 Jan 2024) after it."},
        {"citing_pmcid": "PMC8762369", "retracted_pmid": "",
         "text": "Submission date not available. Published online 22 Dec 2021; the works it cites were retracted between July and November 2021."},
    ],
    "timelines_source": ("Received, accepted and first online dates from the PMC XML and Europe PMC (listfix-20261021/facts.json); "
                         "retraction dates from the PubMed notice or the publisher's Crossref update (" + RED + " class 2a)"),
    "retracted_citing": {
        "PMC11066643": {"notice_pmid": "42581876", "when": "Dec 2025", "note": "Its authors dispute the retraction."},
        "PMC10580988": {"notice_pmid": "42746473", "when": "Sep 2026", "note": "An expression of concern came first, in Jan 2026."},
        "PMC9289514": {"notice_pmid": "40166714", "when": "Mar 2025", "note": ""},
        "PMC11033103": {"notice_pmid": "41395417", "when": "Oct 2025", "note": ""},
        "PMC10841002": {"notice_pmid": "38299313", "when": "2024", "note": ""},
        "PMC6091470": {"notice_pmid": "36698433", "when": "Jan 2023", "note": ""},
        "PMC7041611": {"notice_pmid": "39161888", "when": "Aug 2024", "note": ""},
        "PMC6885654": {"notice_pmid": "33762826", "when": "Mar 2021", "note": ""},
    },
    "retracted_citing_source": "PubMed publication type Retracted Publication and RetractionIn links, read 21 Oct 2026 (listfix-20261021/facts.json)",
}

# ---------------------------------------------------------------- reason class of every cited work on the author list
NOT_RESULTS = {"16807438": "redundant publication", "20068105": "duplicate or redundant publication",
               "29273065": "animal welfare and ethics approval", "31114273": "overlap with the authors' own earlier article"}
NO_REASON = {"31081079": "withdrawn by the authors, no reason given", "31322140": "retracted at the author's request, no reason given",
             "32283217": "withdrawn at the authors' request, no reason given"}
VAGUE = {"31696466": "\"serious inaccuracies and mistakes\", not specified", "32495864": "\"serious inaccuracies and mistakes\", not specified",
         "32196596": "withdrawn \"due to the discovery of new results\""}
NOT_READ = ["14612541", "16033772", "17420722", "17875968", "19190327", "24001238", "25030358", "25311221", "27160836", "27416558",
            "27657824", "29176314", "30007957", "30372802", "30551524", "30585737", "30080301", "31559899", "31838274", "31865777",
            "31933941", "32006899", "32716637", "33347877", "33450262", "34186282", "35033815", "30121199", "32035086"]
works = {w["cited"]: w for w in json.load(open(f"{FIX}/author_works.json"))}
items = json.load(open(f"{SITE}/author_items.json"))
rc = {}
for p in sorted(set(works) | set(items["cited"])):
    n = works.get(p, {}).get("notice", "")
    if p in NOT_RESULTS: rc[p] = {"class": "not the results", "why": NOT_RESULTS[p]}
    elif p in NO_REASON: rc[p] = {"class": "unclear", "why": NO_REASON[p]}
    elif p in VAGUE: rc[p] = {"class": "unclear", "why": VAGUE[p]}
    elif p in NOT_READ: rc[p] = {"class": "unclear", "why": "notice not yet read"}
    else: rc[p] = {"class": "results", "why": "the notice names a problem with the data, images or results"}
    rc[p]["notice_pmid"] = "" if n == "00000000" else n
C["reason_class"] = rc
C["reason_class_source"] = ("Notice text from PubMed, Europe PMC, PMC and publisher pages, read by hand 21 Oct 2026 "
                            "(listfix-20261021/author_works.json and author_works_pass2.json). No item is excluded on this basis.")
# ---------------------------------------------------------------- rate denominators
den = json.load(open(f"{RT}/epmc_rate.json"))
L = json.load(open(f"{SITE}/lists.json"))
C["denominators"] = {
    "what": "Open-access papers in PMC tagged with the author's ORCID iD in Europe PMC, published 2010 to 2026",
    "query": 'AUTHORID:"<orcid>" AND OPEN_ACCESS:y AND IN_PMC:y AND PUB_YEAR:[2010 TO 2026]',
    "counted": DAY, "source": RED + " class 3a (redteam-20261021/epmc_rate.json)",
    "values": {a["orcid"]: den[a["orcid"]]["oa_pmc"] for a in L["authors"]}}
C["fields"] = old.get("fields", [])
json.dump(C, open(out_path, "w"), indent=1, ensure_ascii=False)
print("reason classes", {k: sum(v["class"] == k for v in rc.values()) for k in ("results", "not the results", "unclear")}, "fields kept", len(C["fields"]))
