"""Adds the Huang Y left-off wording correction (its notice is not yet read, so the reason is not asserted)."""
import json, os
P = os.path.expanduser("site/data/phase2/list_corrections.json")
C = json.load(open(P))
f = {"path": "papers/32286091/left_off",
     "old": "Retracted for repeating an earlier paper by the same authors on the same survey. That paper is still published "
            "(Psychiatry Res 2020;288:112954), so citations point to findings that remain in the record.",
     "new": "It appears to repeat an earlier paper by the same authors on the same survey, which is still published "
            "(Psychiatry Res 2020;288:112954), so citations point to findings that remain in the record. We have not yet "
            "read the notice to confirm why it was retracted.",
     "source": "paper_checks.json (reason from search summaries; T&F notice page 403)", "date": "2026-10-21",
     "reason": "The notice is not yet read, so the page must not state the retraction reason as fact (Gate 2)."}
C["fields"] = [x for x in C["fields"] if x["path"] != f["path"]] + [f]
json.dump(C, open(P, "w"), indent=1, ensure_ascii=False)
