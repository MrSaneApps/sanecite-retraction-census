"""Find ClinicalTrials.gov registrations that list a retracted paper among their references.

Frame: every retracted paper in data/stage1_papers.jsonl (22,553). Queries the CT.gov v2 API in batches of PMIDs,
keeps one row per (trial, retracted paper) with the dates needed to tell whether the trial was registered after the
retraction. Output: stories/ctgov_hits.jsonl, log lines with UTC stamps, stories/ctgov_status.txt.
Usage: python3 stories/ctgov_sweep.py
"""
import datetime, json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = f"{HERE}/ctgov_hits.jsonl"; STATUS = f"{HERE}/ctgov_status.txt"
API = "https://clinicaltrials.gov/api/v2/studies"
BATCH = 100


def log(msg):
    line = f"{datetime.datetime.utcnow():%H:%M:%SZ} {msg}"
    print(line, flush=True); open(STATUS, "w").write(line + "\n")


def mdy(s):  # Retraction Watch dates are M/D/YYYY
    try: m, d, y = s.split("/"); return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    except Exception: return None


def get(params, tries=4):
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SaneCite census (hi@saneapps.com)"}), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            log(f"retry {i + 1} {type(e).__name__}: {e}"); time.sleep(5 * (i + 1))
    raise SystemExit("EXIT fail: API unreachable")


papers = {}
for l in open(f"{ROOT}/data/stage1_papers.jsonl"):
    d = json.loads(l)
    if d.get("pmid"): papers[d["pmid"]] = d
pmids = sorted(papers)
log(f"start: {len(pmids)} retracted PMIDs, {(len(pmids) + BATCH - 1) // BATCH} batches")

seen, rows = set(), 0
with open(OUT, "w") as out:
    for b in range(0, len(pmids), BATCH):
        chunk = pmids[b:b + BATCH]
        params = {"query.term": "AREA[ReferencePMID](" + " OR ".join(chunk) + ")", "pageSize": 100, "format": "json"}
        while True:
            d = get(params)
            for s in d.get("studies", []):
                p = s["protocolSection"]; idm = p["identificationModule"]; st = p.get("statusModule", {})
                des = p.get("designModule", {}); refs = p.get("referencesModule", {}).get("references", [])
                for r in refs:
                    pm = r.get("pmid")
                    if pm not in papers or (idm["nctId"], pm) in seen: continue
                    seen.add((idm["nctId"], pm)); rp = papers[pm]
                    out.write(json.dumps({
                        "nct": idm["nctId"], "pmid": pm, "ref_type": r.get("type"), "ref_citation": r.get("citation", "")[:400],
                        "retracted_title": rp.get("title"), "retracted_journal": rp.get("journal"), "retracted": mdy(rp.get("retracted", "")),
                        "retraction_reason": rp.get("reason"), "subject": rp.get("subject"),
                        "trial_title": idm.get("officialTitle") or idm.get("briefTitle"), "brief_title": idm.get("briefTitle"),
                        "first_submitted": st.get("studyFirstSubmitDate"), "start": st.get("startDateStruct", {}).get("date"),
                        "last_update": st.get("lastUpdateSubmitDate"), "status": st.get("overallStatus"),
                        "study_type": des.get("studyType"), "phases": des.get("phases"),
                        "enrollment": des.get("enrollmentInfo", {}).get("count"), "enrollment_type": des.get("enrollmentInfo", {}).get("type"),
                        "conditions": p.get("conditionsModule", {}).get("conditions"),
                        "interventions": [i.get("name") for i in p.get("armsInterventionsModule", {}).get("interventions", [])],
                        "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
                        "countries": sorted({l.get("country") for l in p.get("contactsLocationsModule", {}).get("locations", []) if l.get("country")}),
                    }) + "\n"); rows += 1
            if not d.get("nextPageToken"): break
            params["pageToken"] = d["nextPageToken"]
        out.flush()
        n = b // BATCH + 1
        if n % 10 == 0: log(f"batch {n}: {rows} trial-paper pairs, {len({k[0] for k in seen})} trials")
        time.sleep(0.4)
log(f"EXIT ok: {rows} trial-paper pairs, {len({k[0] for k in seen})} trials, {len({k[1] for k in seen})} retracted papers")
