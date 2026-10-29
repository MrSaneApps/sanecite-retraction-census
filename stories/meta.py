"""Small meta-analysis helpers matching RevMan: M-H fixed or DerSimonian-Laird random risk ratios, and inverse-variance
mean differences (fixed or DL random). Each analysis must reproduce its published estimate before a leave-out counts."""
import math


def _p(z): return math.erfc(abs(z) / math.sqrt(2))


def rr_mh_fixed(rows):
    """rows: (name, events_t, n_t, events_c, n_c). Mantel-Haenszel fixed RR with the Greenland-Robins variance."""
    num = sum(a * n2 / (n1 + n2) for _, a, n1, c, n2 in rows); den = sum(c * n1 / (n1 + n2) for _, a, n1, c, n2 in rows)
    rr = num / den
    P = sum((n1 * n2 * (a + c) - a * c * (n1 + n2)) / (n1 + n2) ** 2 for _, a, n1, c, n2 in rows)
    v = P / (num * den)
    se = math.sqrt(v); m = math.log(rr)
    return rr, math.exp(m - 1.96 * se), math.exp(m + 1.96 * se), _p(m / se)


def rr_dl_random(rows):
    y, v = [], []
    for _, a, n1, c, n2 in rows:
        if a == 0 or c == 0: a, n1, c, n2 = a + .5, n1 + 1, c + .5, n2 + 1
        y.append(math.log((a / n1) / (c / n2))); v.append(1 / a - 1 / n1 + 1 / c - 1 / n2)
    return _dl(y, v, exp=True)


def md(rows, random=True):
    """rows: (name, mean_t, sd_t, n_t, mean_c, sd_c, n_c)."""
    y = [mt - mc for _, mt, st, nt, mc, sc, nc in rows]; v = [st ** 2 / nt + sc ** 2 / nc for _, mt, st, nt, mc, sc, nc in rows]
    if not random:
        w = [1 / x for x in v]; m = sum(a * b for a, b in zip(w, y)) / sum(w); se = math.sqrt(1 / sum(w))
        return m, m - 1.96 * se, m + 1.96 * se, _p(m / se)
    return _dl(y, v, exp=False)


def _dl(y, v, exp):
    w = [1 / x for x in v]; fe = sum(a * b for a, b in zip(w, y)) / sum(w)
    q = sum(a * (b - fe) ** 2 for a, b in zip(w, y)); df = len(y) - 1
    tau2 = max(0.0, (q - df) / (sum(w) - sum(x * x for x in w) / sum(w))) if df > 0 else 0.0
    ws = [1 / (x + tau2) for x in v]; m = sum(a * b for a, b in zip(ws, y)) / sum(ws); se = math.sqrt(1 / sum(ws))
    lo, hi = m - 1.96 * se, m + 1.96 * se
    return (math.exp(m), math.exp(lo), math.exp(hi), _p(m / se)) if exp else (m, lo, hi, _p(m / se))


def report(name, fn, rows, drop, published):
    a = fn(rows); b = fn([r for r in rows if r[0] != drop])
    sig = lambda r: (r[2] < 1 or r[1] > 1) if fn in (rr_mh_fixed, rr_dl_random) else (r[1] > 0 or r[2] < 0)
    print(name, "| published", published)
    print(f"  reproduced: {a[0]:.2f} [{a[1]:.2f}, {a[2]:.2f}] p={a[3]:.2g}")
    print(f"  without {drop}: {b[0]:.2f} [{b[1]:.2f}, {b[2]:.2f}] p={b[3]:.2g}  {'still significant' if sig(b) else 'NO LONGER SIGNIFICANT'}")
