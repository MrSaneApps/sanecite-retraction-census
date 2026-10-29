"""Fetch the publisher pages and Crossref records for the six notices not yet read first-hand."""
import html, json, os, re, time, urllib.request

D = os.path.expanduser("work/listfix/notices7")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
N = {"17962537": "10.1126/science.318.5850.565b", "32421149": "10.1001/jamainternmed.2020.1755",
     "21914820": "10.1242/jcs.098830", "22901075": "10.1021/nn302965w",
     "20710046": "10.1158/0008-5472.CAN-10-2451", "33095058": "10.1080/13548506.2020.1833631"}


def get(url, accept="text/html"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    try:
        r = urllib.request.urlopen(req, timeout=40)
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return 0, url, str(e)


for pmid, doi in N.items():
    code, final, body = get(f"https://doi.org/{doi}")
    open(f"{D}/pub_{pmid}.html", "w").write(body)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S))))
    i = text.lower().find("retract")
    print("==", pmid, doi, code, final, len(body))
    print("   page:", text[max(0, i - 200):i + 900] if i >= 0 else text[:300])
    c2, _, cr = get(f"https://api.crossref.org/works/{doi}", "application/json")
    if c2 == 200:
        m = json.loads(cr)["message"]
        json.dump(m, open(f"{D}/cr_{pmid}.json", "w"))
        print("   crossref:", m.get("title"), "abstract:", (m.get("abstract") or "")[:500], "online:", m.get("published-online"), "print:", m.get("published-print"))
    time.sleep(1)
