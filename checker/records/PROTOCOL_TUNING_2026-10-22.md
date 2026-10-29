# Stage 3 tuning, amendment 1 (written 22 Oct 2026, 12:40 AM ET, before any batch 3 judging)

Owner order, 21 Oct night: iterate in batches of 1,000 until the process is proven.

Batch 2 (seed 2002, sampler v2) is the tuning set. Batch 3 (seed 3003) is the test set. Nothing about batch 3 is
used to choose the method.

Reference sets: 200 random batch 2 pairs (seed 42) and 150 random batch 3 pairs (seed 43), each read blind by
separate Claude sessions and by Muse with the v2 definitions. Where they agree the label is gold; where they disagree a third
careful Claude read with both reasons decides (adjudicated). Gold is still AI-made, not human; a human check comes
before any public claim.

Method choice on batch 2 gold only: among the candidate voters (models x prompt v2/v3 run on batch 2), the panel
of 3-5 voters and vote rule (plurality, twostep, any1, any2) with the highest kappa_error + kappa_major. Ties:
fewer voters, then cheaper.

Test on batch 3: run the chosen panel on all 1,000 pairs (the candidate voters are run on all of batch 3 so the
choice can be applied without re-running). Report: agreement with batch 3 gold (kappa_error, kappa_major,
major precision and recall), and batch 3 rates (major, any error) with Wilson 95% CIs, next to batch 2 and the pilot.
Success bar: kappa_major >= 0.6 and kappa_error >= 0.5 on batch 3 gold, and major rates of batch 2 and batch 3 within
each other's 95% CIs.
