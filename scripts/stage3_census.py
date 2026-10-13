#!/usr/bin/env python3
"""Stage 3 census, codebook v3.1: label every context of every usable pair with ONE model.
Run once per panel model (jev, gemma, clef) in parallel; each writes its own file, so writers never share a file.
usage: SANECITE_DATA=... stage3_census.py <model> <workers>"""
import json, os, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(__file__)); import classify as C
DATA = os.environ["SANECITE_DATA"]; TOKEN = os.environ.get("CF_TOKEN") or os.environ.get("CLOUDFLARE_API_TOKEN") or ""
model, W = sys.argv[1], int(sys.argv[2])
tag = model.split("/")[-1].split("-")[0]
OUT = f"{DATA}/stage3_{tag}.jsonl"
have = set()
if os.path.exists(OUT):
    for l in open(OUT):
        try: r = json.loads(l)
        except Exception: continue
        if r.get("label"): have.add((r["pair_id"], r["ctx"]))
recs = []
for l in open(f"{DATA}/stage2_v31.jsonl"):
    try: r = json.loads(l)
    except Exception: continue  # last line may still be being written by reextract.py
    if r["status"] == "ok" and not r.get("is_notice"): recs.append(r)
todo = [(r, i) for r in recs for i in range(len(r["contexts"])) if (r["pair_id"], i) not in have]
print(time.strftime("%H:%M:%S"), f"STAGE {tag} pairs={len(recs)} todo={len(todo)}", flush=True)
def one(r, i):
    for attempt in range(4):
        try:
            x = C.jev(r, model=model, i=i) if model in ("typesafe/jev", "@cf/cloudflare/clef") else C.chat(model, r, TOKEN, i=i)
        except Exception as e:
            x = {"model": model, "error": f"{type(e).__name__}: {str(e)[:160]}"}
        if x.get("label"): break
        time.sleep(4 * (attempt + 1))
    x.update({"pair_id": r["pair_id"], "ctx": i, "codebook": C.CODEBOOK}); return x
bad = 0
with open(OUT, "a") as f, cf.ThreadPoolExecutor(W) as ex:
    for k, x in enumerate(ex.map(lambda t: one(*t), todo)):
        bad += not x.get("label")
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
        if k % 1000 == 0: f.flush(); print(time.strftime("%H:%M:%S"), f"STAGE {tag} {k}/{len(todo)} errors={bad}", flush=True)
print(time.strftime("%H:%M:%S"), f"EXIT ok {tag} errors={bad}", flush=True)
