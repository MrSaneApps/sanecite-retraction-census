"""Re-run the vitamin C sepsis mortality meta-analyses with and without the retracted trial (Lv et al. 2020).

Study counts are transcribed from each review's published forest plot (images saved beside this file).
Method: risk ratio, DerSimonian-Laird random effects (RevMan "M-H, Random"), which must first reproduce the
published pooled estimate before the leave-out result means anything.
"""
import math

RETRACTED = "Lv"

ANALYSES = {
    "Medicine 2023 (PMC10589557) fig 3, sepsis subgroup; published 0.61 [0.46, 0.82]": [
        ("El Driny 2022", 3, 20, 9, 20), ("Fowler 2014", 4, 8, 5, 8), ("Fowler 2019", 25, 84, 38, 82), ("Lv", 15, 61, 24, 56)],
    "Medicine 2023 (PMC10589557) fig 3, all 8 trials; published 0.68 [0.49, 0.96]": [
        ("El Driny 2022", 3, 20, 9, 20), ("Fowler 2014", 4, 8, 5, 8), ("Fowler 2019", 25, 84, 38, 82), ("Lv", 15, 61, 24, 56),
        ("Lamontagne 2022", 152, 429, 137, 434), ("Rosengrave 2022", 6, 20, 7, 20), ("Wacker 2022", 16, 60, 26, 64),
        ("Zabet 2016", 2, 14, 9, 14)],
    "Front Nutr 2023 (PMC10437115) fig 5, monotherapy; published 0.69 [0.52, 0.93]": [
        ("Fowler 2014", 7, 16, 5, 8), ("Fowler 2019", 25, 84, 38, 82), ("Lamontagne 2022", 152, 429, 137, 434),
        ("Lv", 15, 61, 24, 56), ("Mahmoodpoor 2021", 6, 40, 11, 40), ("Rosengrave 2022", 6, 20, 7, 20),
        ("Wacker 2022", 16, 60, 26, 64), ("Zabet 2016", 2, 14, 9, 14), ("Zhang 2021", 6, 27, 10, 27)],
    "Nutrients 2023 (PMC10146309) fig 2, sepsis; published 0.74 [0.59, 0.91]": [
        ("Aisa-Alvarez 2020", 3, 18, 5, 21), ("El Driny 2022", 3, 20, 9, 20), ("Fowler 2014", 7, 16, 5, 8),
        ("Fowler 2019", 25, 84, 38, 82), ("Gayathri 2022", 1, 19, 2, 18), ("Lamontagne 2022", 152, 429, 137, 434),
        ("Lv", 15, 61, 24, 56), ("Mohamed 2020", 26, 45, 23, 43), ("Nabil Habib 2017", 12, 50, 18, 50),
        ("Niu 2019", 34, 122, 48, 112), ("Rosengrave 2022", 6, 20, 7, 20), ("Reddy 2020", 2, 9, 2, 9),
        ("Wacker 2022", 16, 60, 26, 64), ("Zabet 2016", 2, 14, 9, 14)],
}


def pool(rows):
    y, v = [], []
    for _, a, n1, c, n2 in rows:
        if a == 0 or c == 0: a, n1, c, n2 = a + .5, n1 + 1, c + .5, n2 + 1
        y.append(math.log((a / n1) / (c / n2))); v.append(1 / a - 1 / n1 + 1 / c - 1 / n2)
    w = [1 / x for x in v]; fe = sum(wi * yi for wi, yi in zip(w, y)) / sum(w)
    q = sum(wi * (yi - fe) ** 2 for wi, yi in zip(w, y)); df = len(y) - 1
    tau2 = max(0.0, (q - df) / (sum(w) - sum(x * x for x in w) / sum(w))) if df > 0 else 0.0
    ws = [1 / (x + tau2) for x in v]; m = sum(wi * yi for wi, yi in zip(ws, y)) / sum(ws); se = math.sqrt(1 / sum(ws))
    z = m / se; p = math.erfc(abs(z) / math.sqrt(2))
    return math.exp(m), math.exp(m - 1.96 * se), math.exp(m + 1.96 * se), p


for name, rows in ANALYSES.items():
    a = pool(rows); b = pool([r for r in rows if r[0] != RETRACTED])
    print(name)
    print(f"  reproduced with Lv:  RR {a[0]:.2f} [{a[1]:.2f}, {a[2]:.2f}]  p={a[3]:.4f}")
    print(f"  without Lv:          RR {b[0]:.2f} [{b[1]:.2f}, {b[2]:.2f}]  p={b[3]:.4f}  {'STILL SIGNIFICANT' if b[2] < 1 else 'NO LONGER SIGNIFICANT'}")


# Added after the independent check (VERIFY_1-3.md): the review's Figure 4, duration of vasoactive drugs in sepsis
# (standardised mean difference, Hedges' g, DerSimonian-Laird). Lv carries 56.5% of the weight within the sepsis
# analysis (35.3% is its share of the whole figure, sepsis plus septic shock). Published -0.59
# [-0.99, -0.19] p=0.004; without Lv -0.36 [-1.16, 0.45] p=0.38. The German S3 guideline repeats this finding.
import sys as _s; _s.path.insert(0, __import__("os").path.dirname(__file__) + "/..")
from meta import _dl
def _g(m1, s1, n1, m2, s2, n2):
    sp = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2)); g = (m1 - m2) / sp * (1 - 3 / (4 * (n1 + n2) - 9))
    return g, (n1 + n2) / (n1 * n2) + g * g / (2 * (n1 + n2))
FIG4 = {"El Driny 2022": (55.8, 21.6, 20, 75.6, 33.3, 20), "Fowler 2014": (3.9, 2.25, 8, 3.6, 1.5, 8), "Lv": (25.6, 16.15, 61, 43.8, 31.49, 56)}
for _lab, _keep in [("Fig 4 vasoactive drugs, sepsis, as published", FIG4), ("  without Lv", {k: v for k, v in FIG4.items() if k != "Lv"})]:
    _y, _v = zip(*[_g(*r) for r in _keep.values()]); _m = _dl(list(_y), list(_v), exp=False)
    print(f"{_lab}: SMD {_m[0]:.2f} [{_m[1]:.2f}, {_m[2]:.2f}] p={_m[3]:.3f}")
