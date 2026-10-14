"""Retraction reason groups and field groups, shared by analyze_census.py, coverage_types.py and sensitivity.py.
Amendment 3 (2026-10-14): administrative and process tags are removed before the misconduct/error patterns are
matched (their words, e.g. "duplication of content through error by journal/publisher", used to leak into those
patterns); the misconduct pattern now also catches the Retraction Watch tags it was meant to and missed (compromised
peer review, computer-generated content, rogue editor, hoax, salami slicing, peer review taken over, sabotage);
field is the set of subject codes, not the alphabetically first one."""
import re

ADMIN_G = "administrative (no fault found in the science)"
# Retraction Watch reason tags. "Administrative" = withdrawn with no fault found in the science
# (out of date, replaced by a corrected version, moved journal, a publisher's duplicate).
ADMIN = {"withdrawn as out of date", "retract and replace", "withdrawn to publish in different journal",
         "duplication of content through error by journal/publisher", "error by journal/publisher", "temporary removal"}
# Notice/process tags say nothing about the science, so they are ignored when grouping.
META = {"investigation by journal/publisher", "notice - limited or no information", "date of article and/or notice unknown",
        "upgrade/update of prior notice(s)", "notice - lack of", "notice - unable to access via current resources",
        "investigation by company/institution", "investigation by third party", "investigation by ori", "removed",
        "updated to retraction", "updated to correction", "no further action"}
MISCONDUCT = re.compile(r"fabricat|falsif|manipulat|paper mill|compromised peer review|computer-aided content|"
                        r"computer-generated|rogue editor|hoax|salami|taken via peer review|sabotage|misconduct|"
                        r"plagiar|duplicat|forged|ethical violation")
ERROR = re.compile(r"error|unreliable|concerns/issues about (data|results|image)|not reproducible|contamination")


def tags(s):
    return [t.strip(" +").lower() for t in (s or "").split(";") if t.strip(" +")]


def reason_group(s):
    core = [t for t in tags(s) if t not in META]
    if core and all(t in ADMIN for t in core):
        return ADMIN_G
    j = " ".join(t for t in core if t not in ADMIN)
    if MISCONDUCT.search(j): return "misconduct, fabrication or duplication"
    if ERROR.search(j): return "error or unreliable results"
    return "other or unstated"


def field_group(subj):
    codes = set(re.findall(r"\((\w+)\)", subj or ""))
    if codes == {"BLS"}: return "basic life sciences only"
    if codes == {"HSC"}: return "health sciences only"
    if codes == {"BLS", "HSC"}: return "basic life and health sciences"
    if not codes: return "?"
    return "other fields"
