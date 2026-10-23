"""Edition keys for label rows (EDITIONS.md). Shared by stage3_census.py and analyze_census.py.

A label row belongs to the edition (model, prompt hash). Rows written before 23 Oct 2026 carry no model_id or
prompt_sha256: they are edition 1, whose prompt hash is recorded here. Every version of classify.py in this
repository's history (bdb5de1, 5f2bc1e, b0da4fc) gives the same hash, so it is the hash of the prompt the edition 1
census ran with.
"""
import hashlib, json

EDITION1_CODEBOOK = "v3.3"
EDITION1_PROMPT_SHA = "06e4c3390cc6f0b9c4b7b33546a138f52a8044719c6f810444c4deba62032312"


def prompt_sha(C):
    """Hash of the codebook version, system prompt, examples and answer options of a classify module."""
    return hashlib.sha256(json.dumps([C.CODEBOOK, C.SYSTEM, C.EXAMPLES, C.STANCE, C.USE], ensure_ascii=False,
                                     sort_keys=True).encode()).hexdigest()


def key(row):
    """(model, prompt hash) of a label row. A row without prompt_sha256 is edition 1 if its codebook is edition 1's;
    otherwise its edition is unknown and gets a key of its own, so it can never pass as another edition."""
    model = row.get("model_id") or row.get("model")
    if row.get("prompt_sha256"):
        return (model, row["prompt_sha256"])
    if row.get("codebook") == EDITION1_CODEBOOK:
        return (model, EDITION1_PROMPT_SHA)
    return (model, f"unknown (codebook {row.get('codebook')}, no prompt hash)")
