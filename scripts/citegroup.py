#!/usr/bin/env python3
"""Count how many references share the target's citation group, from the rendered sentence
(the target's in-text citation is marked with →). Mechanical, so the classifier does not have to
notice bundles itself.  Returns (n_refs or None if unparseable, group_text)."""
import re
YEAR = r"(?:19|20)\d\d[a-z]?(?:\s*,\s*[a-z]\b)*"

def _count_numeric(t):
    t = t.replace("→", "")
    n = 0
    for part in re.split(r"[,;]", t):
        part = part.strip()
        m = re.fullmatch(r"(\d+)\s*[-–—‒−]\s*(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2)); n += (b - a + 1) if 0 < b - a < 80 else 2
        else:
            n += len(re.findall(r"\d+", part))
    return n

def _count_authoryear(t):
    n = 0
    for item in re.split(r";", t.replace("→", "")):
        if not re.search(r"(?:19|20)\d\d", item): continue
        ys = re.findall(r"(?:19|20)\d\d([a-z])?((?:\s*,\s*[a-z]\b)*)", item)
        for y, extra in ys: n += 1 + len(re.findall(r"[a-z]", extra))
    return n

def _cite_group_one(s, where="text"):
    k = s.find("→")
    if k < 0: return None, ""
    # 1) inside brackets/parentheses: take the enclosing group, joining adjacent groups "[18], [19]" / "[51]–[53]"
    if k + 1 < len(s) and s[k + 1] in "[(": k += 1  # "→[19]": the arrow sits just before the bracket
    for o, c in (("[", "]"), ("(", ")")):
        lo = s.rfind(o, 0, k + 1); hi = s.find(c, k)
        if lo >= 0 and hi > 0 and s.rfind(c, lo, k) < 0:
            eo, ec = re.escape(o), re.escape(c)
            while True:  # join numeric neighbours: "[18], [19]", "[51]–[53]"
                m = re.search(eo + r"[\d,;–\-\s→]+" + ec + r"[\s,;–\-→]*$", s[:lo])
                if not m: break
                lo = m.start()
            while True:
                m = re.match(r"[\s,;–\-→]*" + eo + r"[\d,;–\-\s→]+" + ec, s[hi + 1:])
                if not m: break
                hi = hi + m.end()
            g = s[lo:hi + 1]; inner = re.sub(r"[\[\]()]", " ", g)
            if "]" in g and "[" in g and re.fullmatch(r"[\s\d,;–\-—‒−→\[\]]+", g):  # joined neighbours: ranges span groups
                inner = re.sub(r"\]\s*([–\-])\s*\[", r"\1", g); inner = re.sub(r"[\[\]]", " ", inner).replace(" ,", ",")
            if re.search(r"(?:19|20)\d\d", inner) and re.search(r"[A-Za-z]{2,}", inner):
                n = _count_authoryear(inner)
                if n: return n, g
            if re.fullmatch(r"[\s\d,;–\-—‒−→]+", inner): return _count_numeric(inner), g
            # e.g. "(e.g. (→22–24))" or "(LoE 1)": try the numeric run around the arrow only
            break
    # 2) table cell or bare author-year list "→Yoshimura et al., 2009; Barnett and Krebs, 2011"
    seg = s
    if where == "table":
        seg = next((c for c in s.split("|") if "→" in c), s)
    if re.match(r"→\s*[A-Z][A-Za-z'’\- ]+(?:et al\.?)?,?\s*(?:19|20)\d\d", s[k:]) or (where == "table" and re.search(r"(?:19|20)\d\d", seg) and re.search(r"[A-Za-z]{3,}", seg)):
        n = _count_authoryear(seg)
        if n: return n, seg.strip()
    # narrative author-year: "→Kerkhoffs et al. (2002) remarked" (one reference unless others are listed beside it)
    if re.match(r"→\s*[A-Z][\w'’\-]+(?:[ ,&]+[A-Z][\w'’\-]+)*(?: et al\.?)?\s*\((?:19|20)\d\d[a-z]?\)", s[k:]):
        near = s[max(0, k - 80):k] + s[k:k + 120].split(")", 1)[-1][:60]
        return (None, "") if re.search(r"\((?:19|20)\d\d[a-z]?\)\s*(?:,|and)", near) else (1, s[k:k + 40])
    # 3) superscript run: digits, commas, dashes and spaces either side of the arrow
    l = k
    while l > 0 and re.match(r"[\d,–\-—‒−\s]", s[l - 1]): l -= 1
    r = k + 1
    while r < len(s) and re.match(r"[\d,–\-—‒−\s→]", s[r]): r += 1
    if l > 0 and s[l - 1].isalpha() and s[l] in "-‐":
        m = re.match(r"[-‐]\d+\s*[,;]?\s*", s[l:k])  # "BMP-12,", "IL-6": the number is part of a name
        if m: l += m.end()
    run = s[l:r].strip(" ,")
    # do not swallow a number that belongs to the text before (e.g. "pH 3" or "in 2016")
    if re.search(r"\d", run.replace("→", "")):
        if l > 0 and re.match(r"[A-Za-z%]", s[l - 1] if not s[l - 1].isspace() else "x"):
            pass
        return _count_numeric(run), run
    return None, ""

def cite_group(s, where="text"):
    """The target may be cited more than once in a sentence ("[73–→76] ... osteosarcoma [→76]").
    Each marked citation is counted alone and the smallest group is returned: if the target stands
    alone anywhere in the sentence, the sentence can rest on it."""
    marks = [i for i, ch in enumerate(s) if ch == "→"]
    if len(marks) <= 1:
        return _cite_group_one(s, where)
    best = (None, "")
    for i in marks:
        one = "".join(ch for j, ch in enumerate(s) if ch != "→" or j == i)
        n, g = _cite_group_one(one, where)
        if n is not None and (best[0] is None or n < best[0]):
            best = (n, g)
    return best if best[0] is not None else _cite_group_one(s, where)


def list_item(s, where="text"):
    """True when the target backs one item of a list on its own: it is alone in its group and the
    sentence carries at least two other citation groups ("liver [4], lung [→5] and gastric [6])."""
    n, g = cite_group(s, where)
    if n != 1: return False
    other = re.sub(re.escape(g), " ", s, count=1) if g else s
    groups = re.findall(r"\[[\d,;–\-\s]+\]|\((?:\d+[,;–\-\s]*)+\)|\([A-Z][^()]*?(?:19|20)\d\d[a-z]?\)", other)
    return len(groups) >= 2


if __name__ == "__main__":
    tests = ["growth in TNBC [→12], and CC [13,14].", "colic episodes [31, →72], between", "(Christensen et al., →2018; Christensen et al., 2016).",
             "retracted meanwhile (→Nunez et al., 2008a,b).", "uptake of metals [18], →[19].", "tumorigenic [51]–→[53] and", "remodeling.20,→21",
             "in which cures are unlikely→9–12.", "(Gupta et al., 2011[→20]).", "| →Yoshimura et al., 2009; Barnett and Krebs, 2011; Barnett et al., 2012",
             "Karalunas et al →29 30 distinguished", "orthologue (e.g. (→22–24)).", "data overload of physicians.120, 121, →122, 123", "[15–→22] (Table 3)",
             "Lee et al. [→22] detected", "(→Han et al., 2011).", "antioxidant [→27], it acts", "consistent with DFT predictions.→42"]
    for t in tests: print(cite_group(t, "table" if t.startswith("|") else "text"), "<-", t)

