#!/usr/bin/env python3
"""Find where a citing paper (Europe PMC open-access JATS XML) cites a given
retracted paper, and return each citing sentence with one sentence either side.

Reference match order: PMID in the ref list, then DOI, then a normalized title
match. In-text markers: <xref ref-type="bibr" rid=...> including ranges like
[3-7] (expanded through the reference order)."""
import gzip, json, os, re, time, urllib.error, urllib.request, xml.etree.ElementTree as ET

UA = {"User-Agent": "SaneCite-Phase2-pilot (hi@saneapps.com)"}

CACHE = os.environ.get("SANECITE_XML_CACHE")  # gzip cache so the census can be re-extracted without refetching

def fetch_xml(pmcid, tries=3):
    path = f"{CACHE}/{pmcid}.xml.gz" if CACHE else None
    if path and os.path.exists(path):
        with gzip.open(path, "rb") as fh: return fh.read()
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read()
            if path:
                tmp = path + ".tmp"
                with gzip.open(tmp, "wb") as fh: fh.write(b)
                os.replace(tmp, path)
            return b
        except urllib.error.HTTPError as e:
            if e.code in (404, 400): return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return None

def norm(s): return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower()).split()

SKIP = {"tex-math", "math", "mml:math", "disp-formula-group"}  # formula markup renders as LaTeX noise

def itertext_clean(el):
    if isinstance(el.tag, str) and (el.tag in SKIP or el.tag.endswith("}math")): return
    if el.text: yield el.text
    for c in el:
        yield from itertext_clean(c)
        if c.tail: yield c.tail

def text_of(el): return re.sub(r"\s+", " ", "".join(itertext_clean(el))).strip()

def strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag: el.tag = el.tag.split("}", 1)[1]
    return root

def find_ref_ids(root, pmid, doi, title, year=None):
    refs = root.findall(".//ref")
    order = [r.get("id") for r in refs]
    tw = norm(title); tset = set(tw)
    hits, soft = [], []
    for r in refs:
        ids = {(p.get("pub-id-type") or "").lower(): (p.text or "").strip().lower() for p in r.iter("pub-id")}
        blob = text_of(r).lower()
        if pmid and (ids.get("pmid") == str(pmid) or f"pmid: {pmid}" in blob or f"/{pmid}" in blob):
            hits.append((r.get("id"), "pmid", blob)); continue
        if doi and (ids.get("doi") == doi or doi in blob):
            hits.append((r.get("id"), "doi", blob)); continue
        at = r.find(".//article-title")
        rt = norm(text_of(at)) if at is not None else []
        other_id = (ids.get("pmid") and ids.get("pmid") != str(pmid)) or (doi and ids.get("doi") and ids.get("doi") != doi)
        yr_ok = not year or any(str(y) in blob for y in (year - 1, year, year + 1))
        if len(tw) >= 5 and rt:
            inter = len(tset & set(rt)) / max(1, len(tset | set(rt)))
            if inter >= 0.8 and not other_id and yr_ok: soft.append((1 + inter, r.get("id"), "title", blob)); continue
        # v3: plain-text references carry no <article-title>; accept the title appearing almost whole in the
        # entry, but only when the entry has no other paper's PMID/DOI and names the original publication year
        # (serial reports such as CDC surveillance share near-identical titles across years).
        if len(tset) >= 6:
            sc = len(tset & set(norm(blob))) / len(tset)
            if sc >= 0.85 and not other_id and yr_ok: soft.append((sc, r.get("id"), "title-in-entry", blob))
    if not hits and soft:  # a fuzzy title match is used only when no exact ID matched, and only the single best entry
        soft.sort(key=lambda t: -t[0]); hits = [soft[0][1:]]
    return hits, order

SENT = re.compile(r"(?<!\bal\.)(?<!\be\.g\.)(?<!\bi\.e\.)(?<!\bFig\.)(?<!\bvs\.)(?<!\bNo\.)(?<=[.!?])\s+(?=[A-Z0-9(\[])")
MARK = "⟦CITE⟧"

def contexts(xml_bytes, pmid, doi, title, max_ctx=3, year=None):
    try: root = strip_ns(ET.fromstring(xml_bytes))
    except ET.ParseError: return {"status": "xml-parse-error"}
    hits, order = find_ref_ids(root, pmid, doi, title, year)
    if not hits: return {"status": "reference-not-found"}
    target = {h[0] for h in hits}
    pos = {rid: i for i, rid in enumerate(order)}
    out, ref_blob = [], hits[0][2]
    body = root.find(".//body")
    if body is None: return {"status": "no-body", "match": hits[0][1]}
    parent = {c: p for p in root.iter() for c in p}
    def section_of(el):
        while el in parent:
            el = parent[el]
            if el.tag == "sec":
                t = el.find("title")
                if t is not None: return text_of(t)
        return ""
    def refnum(r):
        lab = r.find("label")
        m = re.fullmatch(r"\W*(\d{1,4})\W*", text_of(lab)) if lab is not None else None  # "12." / "[12]", never "Smith (2009)"
        return int(m.group(1)) if m else None
    refs = root.findall(".//ref")
    num = {r.get("id"): (refnum(r) or i + 1) for i, r in enumerate(refs)}
    tnums = {num[t] for t in target if t in num}
    numbered = bool(refs) and sum(refnum(r) is not None for r in refs) >= 0.8 * len(refs)  # a true numbered reference list
    BIB = ("bibr", "ref", "bib", None)
    has_bib_xref = any(x.get("ref-type") in BIB and set((x.get("rid") or "").split()) & set(num) for x in root.iter("xref"))
    def nums_in(t):  # "16-19", "3,6", "[4–7, 9]" -> {16,17,18,19}
        out = set()
        for a, b in re.findall(r"(\d+)\s*[-–—‒]\s*(\d+)", t):
            a, b = int(a), int(b)
            if 0 < b - a < 60: out |= set(range(a, b + 1))
        out |= {int(n) for n in re.findall(r"\d+", t)}
        return out
    def enumeration(sent):  # "[1] aged 18-40; [2] singleton; [3] HBsAg..." is a numbered list, not citations
        ns = {int(n) for n in re.findall(r"\[(\d{1,2})\]", sent.replace(MARK, ""))}
        return bool(tnums) and len(ns) >= 3 and {1, 2, 3} <= ns and all(t in ns for t in tnums if t <= 12)
    # a table inside a <p> is skipped as a paragraph and read row by row through its cells instead
    blocks = ([p for p in body.iter("p") if p.find(".//table") is None] +
              [td for td in root.iter("td") if td.find(".//p") is None] +
              [td for td in root.iter("th") if td.find(".//p") is None])
    seen_txt = set()
    for p in blocks:
        xs = list(p.iter("xref"))
        cited = set()
        for i, x in enumerate(xs):
            if x.get("ref-type") not in BIB: continue
            rids = (x.get("rid") or "").split()
            if target & set(rids): cited.add(i); continue
            xt = text_of(x)
            NUMERIC = re.fullmatch(r"[\[(]?\s*\d+(?:\s*[-–—‒,;]\s*\d+)*\s*[\])]?", xt.strip())
            if NUMERIC and tnums and rids and rids[0] in num and num[rids[0]] in nums_in(xt) and tnums & nums_in(xt): cited.add(i); continue
            if i + 1 < len(xs) and (x.tail or "").strip() in ("-", "–", "—", "‒"):
                a = [pos.get(r) for r in rids if r in pos]; b = [pos.get(r) for r in (xs[i + 1].get("rid") or "").split() if r in pos]
                if a and b and any(min(a) < pos.get(t, -1) < max(b) for t in target): cited.add(i)
        plain = None
        if not cited and not has_bib_xref and tnums and numbered:  # numbered references cited as plain text, no links
            ptxt = text_of(p)
            plain = [m for m in re.finditer(r"[\[(]\s*(\d+(?:\s*[-–—‒,;]\s*\d+)*)\s*[\])]", ptxt) if tnums & nums_in(m.group(1))]
            if not plain: continue
        elif not cited: continue
        for i, x in enumerate(xs):
            x.attrib["_mark"] = "1" if i in cited else "0"
        def render(el):
            if el.tag in SKIP: return ""
            s = el.text or ""
            kids = list(el)
            for j, c in enumerate(kids):
                if c.tag == "xref":  # an xref with no visible text (rendered superscript by CSS) gets its reference number
                    rid = (c.get("rid") or "").split()[:1]
                    xt = text_of(c) or (str(num[rid[0]]) if rid and rid[0] in num and c.get("ref-type") in BIB else "")
                    s += (MARK if c.attrib.get("_mark") == "1" else "") + xt
                else: s += render(c)
                # adjacent superscript xrefs with nothing between them ("41""42") would read as "4142"
                if c.tag in ("xref", "sup") and not (c.tail or "").strip() and j + 1 < len(kids) and kids[j + 1].tag in ("xref", "sup") \
                        and re.search(r"\d$", s) and re.match(r"\s*\d", text_of(kids[j + 1])):
                    s += ","
                s += c.tail or ""
            return s
        if plain:
            ptxt = text_of(p); para = ""; k = 0
            for m in plain: para += ptxt[k:m.start()] + MARK + m.group(0); k = m.end()
            para = re.sub(r"\s+", " ", para + ptxt[k:]).strip()
        else:
            para = re.sub(r"\s+", " ", render(p)).strip()
        where = "text"
        if p.tag in ("td", "th"):  # a table row: show the whole row plus the table caption
            where = "table"
            row = parent.get(p)
            cells = [re.sub(r"\s+", " ", render(c) if c is p else text_of(c)).strip() for c in (list(row) if row is not None else [p])]
            wrap = p
            while wrap is not None and wrap.tag != "table-wrap": wrap = parent.get(wrap)
            cap = text_of(wrap.find("caption")) if wrap is not None and wrap.find("caption") is not None else ""
            sents = [" | ".join(cells)]; para = sents[0]
            key = para
            if key in seen_txt: continue
            seen_txt.add(key)
            out.append({"section": section_of(p), "where": where, "before": ("Table: " + cap)[:300] if cap else "",
                        "sentence": para.replace(MARK, "→"), "after": ""})
            if len(out) >= max_ctx: break
            continue
        # superscript styles put the citation after the full stop ("reports.39 VEGF ..."): split there too
        para = re.sub(r"(?<=[A-Za-z)\]])([.!?]\s?[\[(]?(?:" + MARK + r")?\d+(?:\s*[,–\-]\s*(?:" + MARK + r")?\d+)*[\])]?)\s+(?=[A-Z])", "\\1\n", para)
        sents = [x for part in para.split("\n") for x in SENT.split(part)]
        for j, s_ in enumerate(sents):
            if MARK in s_ and not enumeration(s_):
                out.append({"section": section_of(p), "where": where, "before": sents[j - 1] if j else "",
                            "sentence": s_.replace(MARK, "→"), "after": sents[j + 1] if j + 1 < len(sents) else ""})
            if len(out) >= max_ctx: break
        if len(out) >= max_ctx: break
    full = text_of(body).lower()
    art = root.find(".//article") if root.tag != "article" else root
    atype = (art.get("article-type") if art is not None else "") or ""
    tg = root.find(".//article-title"); title_txt = text_of(tg).lower() if tg is not None else ""
    is_notice = atype.lower() in ("retraction", "correction", "expression-of-concern", "removal", "addendum", "editorial-note") or \
        bool(re.match(r"(retraction|retracted|expression of concern|correction|erratum|corrigendum|notice of)", title_txt))
    for c in out:  # the target may be cited again in a neighbouring sentence: show it as the arrow too
        for k in ("before", "sentence", "after"): c[k] = c[k].replace(MARK, "\u2192")
    return {"status": "ok" if out else "no-in-text-citation", "match": hits[0][1], "contexts": out,
            "n_contexts_capped": len(out), "ref_entry": ref_blob[:400],
            "ref_entry_flags_retraction": bool(re.search(r"retract", ref_blob)),
            "doc_mentions_retract": bool(re.search(r"retract", full)),
            "article_type": atype, "is_notice": is_notice}
