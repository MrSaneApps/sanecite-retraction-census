"""Notice text for retracted works, by the work's PMID: PubMed RetractionIn link, then the notice's PubMed abstract,
then its PMC page. Prints up to 1500 characters each and saves everything to notices_<tag>.json."""
import html, json, os, re, sys, time, urllib.request

W = os.path.expanduser("work/listfix")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}


def get(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode("utf-8", "replace")
    except Exception:
        return ""


def clean(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)))).strip()


out = {}
for p in sys.argv[2].split(","):
    x = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={p}&retmode=xml")
    title = clean((re.findall(r"<ArticleTitle>(.*?)</ArticleTitle>", x, re.S) or [""])[0])
    ns = re.findall(r'RefType="RetractionIn"><RefSource>(.*?)</RefSource>(?:<PMID[^>]*>(\d+)</PMID>)?', x)
    own = clean(" ".join(re.findall(r"<AbstractText.*?>(.*?)</AbstractText>", x, re.S))) if title.lower().startswith(("retract", "withdraw")) else ""
    text, src, npmid = own, "PubMed record of the work (replaced by the notice)" if own else "", ""
    for ref, n in ns:
        npmid = n
        if not n or text:
            continue
        y = get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={n}&retmode=xml")
        ab = clean(" ".join(re.findall(r"<AbstractText.*?>(.*?)</AbstractText>", y, re.S)))
        pmc = (re.findall(r'<ArticleId IdType="pmc">(.*?)<', y) or [""])[0]
        if len(ab) > 80:
            text, src = ab, f"PubMed abstract of notice {n}"
        elif pmc:
            b = clean(get(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmc}/"))
            i = b.find("PMCID:")
            if i > 0:
                text, src = b[i:i + 3000], f"PMC page {pmc} of notice {n}"
        time.sleep(0.4)
    out[p] = {"title": title, "notice_pmid": npmid, "notices": ns, "src": src, "text": text}
    print(f"== {p} | {title[:90]} | notice {npmid} | {src}\n   {text[:1500]}\n")
    time.sleep(0.4)
json.dump(out, open(f"{W}/notices_{sys.argv[1]}.json", "w"), indent=1)
