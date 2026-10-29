#!/usr/bin/env python3
"""Rank panel + vote rule by the WORSE of their scores on two gold sets (kappa_error + kappa_major), so a panel that only
fits one set cannot win. Usage: robust_pick.py AGG_A.json AGG_B.json [--top 15]"""
import json, sys

a = {(r["panel"], r["rule"]): r for r in json.load(open(sys.argv[1]))}
b = {(r["panel"], r["rule"]): r for r in json.load(open(sys.argv[2]))}
top = int(sys.argv[4]) if len(sys.argv) > 4 else 15
s = lambda r: (r["kappa_error"] or 0) + (r["kappa_major"] or 0)
rows = sorted(((min(s(a[k]), s(b[k])), (s(a[k]) + s(b[k])) / 2, k) for k in set(a) & set(b)), key=lambda x: (-x[0], -x[1]))
print("panels in both:", len(rows))
for m, avg, k in rows[:top]:
    x, y = a[k], b[k]
    print("min=%.3f avg=%.3f %-9s %s\n      A kE=%s kM=%s ct=%s | B kE=%s kM=%s ct=%s"
          % (m, avg, k[1], k[0], x["kappa_error"], x["kappa_major"], x["pred_cannot_tell"], y["kappa_error"], y["kappa_major"], y["pred_cannot_tell"]))
ch = ("v2:deepseek-v4.1-flash-1017+v2:gpt-oss-120b+v2:kimi-k2.6+v2:llama-3.3-70b-instruct-fp8-fast+v3:gpt-oss-120b", "plurality")
if ch in a and ch in b:
    print("FIRST CHOICE (picked on A only): A", a[ch]["kappa_error"], a[ch]["kappa_major"], "B", b[ch]["kappa_error"], b[ch]["kappa_major"])
