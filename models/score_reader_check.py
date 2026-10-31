# Scorer for the 31 Oct 2026 Lists reader check (exact verdict agreement, per-verdict agreement, HOLDS vs not).
# Published as code only: its key (calib_key.json) names entries not yet public, so the key and reads are not here.
#!/usr/bin/env python3
"""Score wave-1 calibration reads against calib_key.json (CALIB_RULE.md): exact agreement per reader (bar 85%),
per-verdict agreement, and the HOLDS / not-HOLDS split. Prints counts only, never article text.
usage: score_calib.py READS.jsonl [READS.jsonl ...]"""
import collections, json, os, sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key = {int(k): v for k, v in json.load(open(os.path.join(HERE, "calib_key.json")))["key"].items()}


def kv(v):
    return v["verdict"] if isinstance(v, dict) else v


for fn in sys.argv[1:]:
    rows = {}
    for l in open(fn):
        if l.strip():
            j = json.loads(l)
            rows[j["draw"]] = j
    got = {d: (r.get("parsed") or {}).get("verdict") for d, r in rows.items()}
    read = [d for d in key if got.get(d)]
    agree = sum(got[d] == kv(key[d]) for d in read)
    per = collections.defaultdict(lambda: [0, 0])
    conf = collections.Counter()
    for d in read:
        k = kv(key[d]); per[k][1] += 1; per[k][0] += got[d] == k
        if got[d] != k:
            conf[(k, got[d])] += 1
    hk = sum((got[d] == "HOLDS") == (kv(key[d]) == "HOLDS") for d in read)
    out = {"file": os.path.basename(fn), "keyed": len(key), "read": len(read), "not_read": len(key) - len(read),
           "exact": f"{agree}/{len(read)} = {agree / len(read):.3f}" if read else None,
           "bar_85": bool(read) and agree / len(read) >= 0.85,
           "holds_vs_not": f"{hk}/{len(read)} = {hk / len(read):.3f}" if read else None,
           "per_verdict": {k: f"{a}/{n}" for k, (a, n) in sorted(per.items())},
           "misses (key -> read)": {f"{a} -> {b}": n for (a, b), n in conf.most_common()}}
    print(json.dumps(out, indent=1))
