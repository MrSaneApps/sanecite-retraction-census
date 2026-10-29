"""Facts the Lists corrections rest on, pulled fresh from Europe PMC, PubMed and Crossref, saved as evidence."""
import csv, json, os, re, time, urllib.parse, urllib.request

W = os.path.expanduser("work/listfix")
P2 = os.path.expanduser("site/data/phase2")
UA = {"User-Agent": "SaneCite research (hi@saneapps.com)"}


def get(url):
    for _ in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2)
    return ""


def epmc(pmcids):
    q = " OR ".join(f"PMCID:{p}" for p in pmcids)
    d = json.loads(get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(
        {"query": q, "format": "json", "resultType": "core", "pageSize": 100})))
    return {r["pmcid"]: r for r in d["resultList"]["result"]}


out = {}
# (a) straddles: article history from the PMC XML, first online date from Europe PMC
STRADDLE = ["PMC10716031", "PMC10826439", "PMC8100681", "PMC8862212", "PMC8916230", "PMC10902086", "PMC9808980",
            "PMC10887337", "PMC8762369", "PMC10278211", "PMC10761534"]
meta = epmc(STRADDLE)
hist = {}
for p in STRADDLE:
    x = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={p[3:]}&retmode=xml")
    h = {}
    for typ, body in re.findall(r'<date date-type="([^"]+)"[^>]*>(.*?)</date>', x, re.S):
        parts = {k: v for k, v in re.findall(r"<(day|month|year)>(\d+)</", body)}
        h[typ] = "-".join(parts.get(k, "00").zfill(2) for k in ("year", "month", "day"))
    for typ, body in re.findall(r'<pub-date[^>]*pub-type="([^"]+)"[^>]*>(.*?)</pub-date>', x, re.S):
        parts = {k: v for k, v in re.findall(r"<(day|month|year)>(\d+)</", body)}
        h["pub:" + typ] = "-".join(parts.get(k, "00").zfill(2) for k in ("year", "month", "day"))
    m = meta.get(p, {})
    hist[p] = {"history": h, "first_online": m.get("firstPublicationDate"), "doi": m.get("doi"), "title": m.get("title"),
               "journal": (m.get("journalInfo") or {}).get("journal", {}).get("isoabbreviation")}
    print("straddle", p, hist[p]["first_online"], h)
    time.sleep(0.4)
out["straddle"] = hist
# PMC8762369: Crossref has no history; try the publisher record through Crossref's assertion list
cr = get("https://api.crossref.org/works/" + (hist["PMC8762369"]["doi"] or ""))
try:
    m = json.loads(cr)["message"]
    out["PMC8762369_crossref"] = {"assertion": m.get("assertion"), "published-online": m.get("published-online"), "created": m.get("created", {}).get("date-time")}
except Exception:
    out["PMC8762369_crossref"] = {}
print("PMC8762369 crossref", out["PMC8762369_crossref"])

# (b) citing papers that are themselves retracted: PubMed publication types
RETR = ["PMC11066643", "PMC10580988", "PMC9289514", "PMC11033103", "PMC10841002", "PMC6091470", "PMC7041611", "PMC6885654"]
conv = json.loads(get("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?format=json&ids=" + ",".join(RETR)))
pm = {r["pmcid"]: r.get("pmid") for r in conv.get("records", [])}
rs = {}
for p in RETR:
    x = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pm[p]}&retmode=xml")
    types = re.findall(r"<PublicationType[^>]*>(.*?)</PublicationType>", x)
    rin = re.findall(r'<CommentsCorrections RefType="(RetractionIn|ExpressionOfConcernIn)"><RefSource>(.*?)</RefSource>(?:<PMID[^>]*>(\d+)</PMID>)?', x)
    title = (re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", x) or [""])[0]
    rs[p] = {"pmid": pm[p], "types": types, "notices": rin, "title": title}
    print("retracted?", p, pm[p], "Retracted Publication" in types, rin)
    time.sleep(0.4)
out["retracted_citing"] = rs

# (c) journal-sample items to drop: TREEFINDER and the wrong-journal miR-144 paper
checks = list(csv.DictReader(open(f"{P2}/list_checks.csv", newline="")))
for c in checks:
    if c["list"] == "journal" and (re.search(r"TREEFINDER", c["note"], re.I) or c["entry"] == "Bioengineered" and re.search(r"miR-144", c["note"])):
        print("journal sample", c["entry"], c["pair_id"], c["second_reading"], c["note"][:200])
out["review_types"] = {p: (r.get("pubTypeList") or {}).get("pubType", []) for p, r in epmc(["PMC10761534", "PMC8695688", "PMC10278211"]).items()}
print(out["review_types"])
json.dump(out, open(f"{W}/facts.json", "w"), indent=1)
