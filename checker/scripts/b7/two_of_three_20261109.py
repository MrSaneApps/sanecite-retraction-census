"""Supplement to the registered score_b7.py (unchanged): the 2-of-3 view's major and any-error rates, which the score
note of 5 Nov 2026 reports (101 of 1,191; 187 of 1,191) but SCORE_B7_2026-11-05.json does not store. Same inputs and
the same majority rule as score_b7.py lines 123-129; on the disagreement items the 2-of-3 majority replaces the
third-read key. Written 9 Nov 2026 for the site figure (owner yes 7 Nov: any-error shown both ways)."""
import copy, json, sys
sys.argv = ["score_b7.py"]
import score_b7 as S  # import guard checked: main() runs only under __main__

src = open(S.__file__).read()
assert "if __name__ == \"__main__\":" in src

a, mu, key, adj, n_sample, third = S.load("b7")
dis = [d for d in key if key[d].get("source") == "adjudicated" and d in third and d in a and d in mu]
alt = copy.deepcopy(key)
for d in dis:
    vs = [a[d]["verdict"], mu[d]["verdict"], third[d]]
    top = max(set(vs), key=vs.count)
    alt[d]["verdict"] = top if vs.count(top) >= 2 else "cannot_tell"
judged_key = sorted(d for d in key if key[d]["verdict"] != "cannot_tell")
judged_alt = sorted(d for d in alt if alt[d]["verdict"] != "cannot_tell")
out = {"note": __doc__.strip(), "disagreement_items": len(dis),
       "key_view": {"major": S.rate(judged_key, key, ("major",)), "any_error": S.rate(judged_key, key, ("major", "minor"))},
       "two_of_three_view": {"major": S.rate(judged_alt, alt, ("major",)), "any_error": S.rate(judged_alt, alt, ("major", "minor"))}}
print(json.dumps(out, indent=1))
