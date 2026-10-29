# Method choice 3 (amendment 3), 22 Oct 2026, 4:05 AM ET, before any batch 5 sampling or judging

## Result of choice 2 on its test (batch 4)
Twostep panel of 5 Cloudflare models on batch 4 gold (150): kappa_error 0.580 (bar 0.5, pass), kappa_major 0.366
(bar 0.6, FAIL). It finds most major errors (recall 0.80) but calls about three times too many (precision 0.27).
No vote-count rule over the 5 voters clears both bars on all three gold sets (best worst-case: e>=2, m>=3).
Ceiling check: the two blind reference readers (Claude, Muse) agree with each other at kappa_error 0.58-0.75 and
kappa_major 0.74-0.85; the panel reaches 0.35-0.70 on major against either. The cheap panel is the limit.

## Choice 3: two stages
Stage 1: the twostep panel (choice 2) reads every citation. Citations it calls accurate are final.
Stage 2: Muse (judge_v2.py --models muse, same prompt as the reference reads) reads every citation the panel calls
minor, major or cannot_tell; Muse's verdict is final for those.
Seen post hoc on batches 2-4 (against Claude's blind reads; Muse is not independent of the gold sets, so Claude
alone is the reference here): kappa_major 0.834 / 0.849 / 0.743; kappa_error 0.642 / 0.522 / 0.630;
27% of citations go to stage 2.

## Test (batch 5, seed 5005, 200 pairs) and its reference (150 pairs, seed 55)
Reference: Claude blind reads only (6 packets of 25, same instructions as before); Muse is part of the method, so it
is not used as reference.
Success bar: kappa_major >= 0.6 and kappa_error >= 0.5, two-stage verdict against Claude reference (cannot_tell on
either side excluded), as in amendment 1.
Rates for the batch reported with Wilson 95% CIs.
