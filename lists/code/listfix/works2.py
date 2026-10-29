"""Second pass for notices with no usable text: the notice's PMC page, then the notice DOI's landing page."""
import html, json, os, re, sys, time, urllib.request

W = os.path.expanduser("work/listfix")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
works = json.load(open(f"{W}/author_works.json"))
want = set(sys.argv[1].split(","))


def get(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)


def text(body):
    b = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<header.*?</header>|<footer.*?</footer>", "", body, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", b))).strip()


out = {}
for w in works:
    if w["cited"] not in want or not w["notice"] or w["notice"] == "00000000":
        continue
    _, x = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={w['notice']}&retmode=xml")
    pmc = (re.findall(r'<ArticleId IdType="pmc">(.*?)<', x) or [""])[0]
    doi = (re.findall(r'<ArticleId IdType="doi">(.*?)<', x) or [""])[0]
    got, src = "", ""
    if pmc:
        c, b = get(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc}/")
        t = text(b)
        i = t.find("PMCID:")
        if c == 200 and i > 0:
            got, src = t[i:i + 2500], f"PMC page of notice {pmc}"
    if not got and doi:
        c, b = get(f"https://doi.org/{doi}")
        t = text(b)
        if c == 200:
            j = max(t.lower().find("retract"), 0)
            got, src = t[max(0, j - 300):j + 2000], f"publisher page doi:{doi}"
        else:
            src = f"publisher page doi:{doi} returned {c}"
    out[w["cited"]] = {"notice": w["notice"], "pmc": pmc, "doi": doi, "src": src, "text": got}
    print("==", w["cited"], w["first"], w["journal"], "|", src, "|", got[:900])
    time.sleep(0.5)
json.dump(out, open(f"{W}/author_works_pass2.json", "w"), indent=1)
