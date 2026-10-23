#!/usr/bin/env python3
"""Tests for the release checks: editions never mix, the manifest catches a deleted file, the staging scan stops.

usage: python3 scripts/test_release_checks.py   (no network, no model calls; temporary folders only)
"""
import json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import editions as E, stage_release as S


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for r in rows: f.write(json.dumps(r) + "\n")


def legacy(i, model="typesafe/jev"):   # a row as the edition 1 census wrote it (no model_id, no prompt hash)
    return {"model": model, "pair_id": f"p{i}", "ctx": 0, "codebook": "v3.3", "label": "substantive"}


class Editions(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d)

    def run_script(self, *args):
        env = dict(os.environ, SANECITE_DATA=self.d, CF_TOKEN="", CLOUDFLARE_API_TOKEN="")
        return subprocess.run([sys.executable, os.path.join(HERE, args[0]), *args[1:]], env=env,
                              capture_output=True, text=True, timeout=120)

    def test_edition1_hash_is_the_current_prompt(self):
        import classify as C
        self.assertEqual(E.prompt_sha(C), E.EDITION1_PROMPT_SHA)

    def test_legacy_row_is_edition1(self):
        self.assertEqual(E.key(legacy(1)), ("typesafe/jev", E.EDITION1_PROMPT_SHA))
        self.assertNotEqual(E.key({**legacy(1), "codebook": "v3.1"})[1], E.EDITION1_PROMPT_SHA)

    def test_analysis_stops_on_a_mixed_legacy_file(self):
        rows = [legacy(i) for i in range(3)]
        rows.append({**legacy(9, "typesafe/jev-v2"), "model_id": "typesafe/jev-v2", "prompt_sha256": "f" * 64})
        write_jsonl(os.path.join(self.d, "stage3_jev.jsonl"), rows)
        r = self.run_script("analyze_census.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("more than one edition", r.stderr)

    def test_analysis_accepts_edition1_rows_with_and_without_fields(self):
        rows = [legacy(i) for i in range(3)]
        rows.append({**legacy(9), "model_id": "typesafe/jev", "prompt_sha256": E.EDITION1_PROMPT_SHA})
        write_jsonl(os.path.join(self.d, "stage3_jev.jsonl"), rows)
        r = self.run_script("analyze_census.py")   # gets past the edition check, then lacks stage2 (not made here)
        self.assertNotIn("more than one edition", r.stderr)

    def test_labeller_refuses_a_new_model_in_a_legacy_file(self):
        write_jsonl(os.path.join(self.d, "stage3_jev.jsonl"), [legacy(i) for i in range(3)])
        r = self.run_script("stage3_census.py", "typesafe/jev-v2", "1")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("another edition", r.stderr)

    def test_labeller_continues_edition1_with_the_same_model(self):
        write_jsonl(os.path.join(self.d, "stage3_jev.jsonl"), [legacy(i) for i in range(3)])
        write_jsonl(os.path.join(self.d, "stage2_v31.jsonl"), [])   # nothing left to label: no model call
        r = self.run_script("stage3_census.py", "typesafe/jev", "1")
        self.assertEqual(r.returncode, 0, r.stderr)


class Manifest(unittest.TestCase):
    def test_deleted_registered_file_fails(self):
        d = tempfile.mkdtemp()
        try:
            subprocess.run(["git", "clone", "-q", ROOT, d], check=True)
            shutil.copy(os.path.join(HERE, "verify_manifest.py"), os.path.join(d, "scripts", "verify_manifest.py"))
            v = [sys.executable, os.path.join(d, "scripts", "verify_manifest.py")]
            subprocess.run(v + ["--update", "test"], capture_output=True, text=True)   # this working copy's files
            ok = subprocess.run(v, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stdout)
            subprocess.run(["git", "-C", d, "rm", "-q", "data/census_results.json"], check=True)
            bad = subprocess.run(v, capture_output=True, text=True)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("MISSING    data/census_results.json", bad.stdout)
        finally:
            shutil.rmtree(d)


class Scan(unittest.TestCase):
    def test_rules(self):
        cases = {"see /Users/x/notes": "private path", "on the Mini today": "machine name",
                 "Claude subagents read it": "agent name", "key in sane-env": "secret store",
                 "safety stop, SOP C8": "internal procedure", "ACCOUNT_ID:-" + "ab12" * 8: "account id",
                 "SaneApps/outputs/x": "private folder"}
        for text, rule in cases.items():
            self.assertTrue(any(rule in b for b in S.check_text("x.md", text, {})), text)
        self.assertEqual(S.check_text("x.md", "write to hi@saneapps.com", {}), [])
        self.assertTrue(S.check_text("x.md", "write to someone@example.org", {}))
        self.assertEqual(S.check_text("data/x.jsonl", "the Mini-Mental State Exam", {}), [])   # data: hard rules only
        self.assertEqual(S.check_text("x.md", "on the Mini", {"machine name": "why"}), [])

    def test_quotes_and_pending(self):
        self.assertTrue(S.keys_in([{"parsed": {"quote": "x"}}], S.QUOTE_KEYS))
        self.assertFalse(S.keys_in([{"quote_found": True}], S.QUOTE_KEYS))
        self.assertEqual(S.drop_keys({"a": 1, "parsed": {"quote": "x", "v": 2}}, S.QUOTE_KEYS), {"a": 1, "parsed": {"v": 2}})

    def test_hash_log(self):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "log.txt")
            open(p, "w").write("a" * 64 + "  x.md\n# note\n2026-10-23T19:40:55Z " + "b" * 64 + "  x.md  (later)\n")
            self.assertEqual(S.hash_log(p), {"x.md": "b" * 64})
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
