"""One row per cited work on the author list: its retraction notice and the notice text, from the red-team pull,
with missing texts filled from PubMed, Europe PMC full text and OpenAlex (in that order)."""
import html, json, os, re, time, urllib.parse, urllib.request

W = os.path.expanduser("work/listfix")
RT = os.path.expanduser("work/top10/redteam-20261021")
D = json.load(open(f"{RT}/sweep_raw.json"))
A = json.load(open(f"{RT}/A2.json"))
UA = {"User-Agent": "SaneCite research (hi@saneapps.com)"}


def get(url):
    for _ in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2)
    return ""


def clean(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


works = {}
for r in A:
    w = works.setdefault(r["cited"], {"cited": r["cited"], "first": r["first"], "journal": r["cj"], "year": r["cy"],
                                      "notice": r["notice"], "items": 0, "owners": set(), "text": "", "src": ""})
    w["items"] += 1
    w["owners"].add(r["owner"])
for p, w in works.items():
    n = w["notice"]
    t = (D["pm_notice"].get(n, {}) or {}).get("abstract") or ""
    if len(t) >= 60:
        w["text"], w["src"] = clean(t), f"PubMed abstract of notice PMID {n}"
        continue
    t = ((D.get("epmc_notice") or {}).get(n, {}) or {}).get("text") or ""
    if len(t) >= 60 and not t.startswith("ERR"):
        w["text"], w["src"] = clean(t), f"Europe PMC full text of notice PMID {n}"
missing = [w for w in works.values() if not w["text"] and w["notice"]]
print("works", len(works), "with text", len(works) - len(missing), "missing", len(missing))
for w in missing:
    n = w["notice"]
    x = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={n}&retmode=xml")
    ab = clean(" ".join(re.findall(r"<AbstractText.*?>(.*?)</AbstractText>", x, re.S)))
    doi = (re.findall(r'<ArticleId IdType="doi">(.*?)<', x) or [""])[0]
    pmc = (re.findall(r'<ArticleId IdType="pmc">(.*?)<', x) or [""])[0]
    w["notice_doi"], w["notice_pmc"] = doi, pmc
    if len(ab) >= 60:
        w["text"], w["src"] = ab, f"PubMed abstract of notice PMID {n}"
    elif pmc:
        ft = get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmc}/fullTextXML")
        body = clean(re.sub(r"<ref-list.*?</ref-list>", "", (re.findall(r"<body>(.*?)</body>", ft, re.S) or [""])[0], flags=re.S))
        if len(body) >= 60:
            w["text"], w["src"] = body, f"Europe PMC full text of notice {pmc}"
    if not w["text"] and doi:
        o = get(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}?mailto=hi@saneapps.com")
        try:
            inv = json.loads(o).get("abstract_inverted_index") or {}
            t = " ".join(wd for _, wd in sorted((i, wd) for wd, ix in inv.items() for i in ix))
            if len(t) >= 60 and "ADVERTISEMENT" not in t[:40]:
                w["text"], w["src"] = t, f"OpenAlex copy of notice doi:{doi}"
        except Exception:
            pass
    time.sleep(0.4)
for w in works.values():
    w["owners"] = sorted(w["owners"])
json.dump(sorted(works.values(), key=lambda w: w["cited"]), open(f"{W}/author_works.json", "w"), indent=1)
print("still missing", sum(not w["text"] for w in works.values()))
