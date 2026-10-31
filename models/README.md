# Models: how SaneCite picks the AI models that read citations

Every model test SaneCite has run, from the first bake-off on 13 Oct 2026 to the reader checks on 31 Oct 2026, with
the records behind each number. No model is trusted on its word: each one is scored against an answer key first.

## Read this first

Every answer key here was made by AI models, not by people, except one: the comparison with Hsiao and Schneider's
hand-checked labels (test T09). A score means "agrees with our AI key", not "is right". Most keys are small, and some
are stratified on purpose (the row says so). A human check of a sample is designed and still to come.

## The scoreboard (`scoreboard.csv`)

One row per model, setup and test. `row_id` is stable (T01-01 and so on); `test_id` groups the rows of one test.

| Column | Meaning |
|---|---|
| `answer_key` | What the model was scored against, its size, and whether AI or people made it |
| `model`, `maker`, `host` | Public model name, its maker, and where it ran |
| `setting` | Effort or thinking, citations per call, prompt version |
| `role` | screen, decider, reader, panel member, backup reader or candidate |
| `metric`, `k`, `n`, `value` | The main score as a count (k of n) and as a share, rounded once |
| `kappa` | Agreement beyond chance, with the classes it compares (for example major vs not major) |
| `cost_per_1000_citations_usd`, `cost_basis` | Cost and how it was worked out: list price (usage times the published price on the date given) or billed |
| `refusal_or_stop_rate` | Refusals, safety stops or failed calls, as k/n, where recorded |
| `outcome`, `why` | chosen, backup, rejected or candidate, and one plain reason |
| `public_record` | Where to check the number: a file in this repository or on sanecite.com, or "not public yet" |
| `other_metrics` | Secondary scores (precision, flag rate, AUC) |

Two tasks appear. Census labelling (T01-T09, T21): does a citing paper use retracted work as support, mention it in
passing, or show it knows of the retraction? Citation accuracy (T10-T20, T22-T24): does a citation say what the cited
paper says? There the main measures are recall of "major" errors, precision of major calls, and kappa for major vs not.

## Other files

See `MANIFEST.md` for each file, where it came from and what we changed. Records that hold passages from other
authors' papers are not published; rows give IDs instead. Cloudflare Workers AI model ids are written without their
leading at-sign (for example cf/cloudflare/clef).

## Ideas welcome

If you see a better model, setting or test, or a mistake in ours, open an issue at
https://github.com/MrSaneApps/sanecite-retraction-census/issues
