# SaneCite census codebook, v3.3 (frozen 2026-10-13)

This text is generated from `scripts/classify.py` (STANCE, USE, EXAMPLES, label()), which is what the models were given.

Unit: one citing paper citing one retracted paper. Each passage (the sentence carrying the in-text citation, one
sentence either side, up to three passages per citing paper) is read separately. The arrow → marks the citation.
Readers are not told the cited work was retracted.

## Question 1, stance
- **disputed**: Anywhere in the TEXT, including the sentences before and after the citation, or in the section heading, the target itself is called retracted, withdrawn, fraudulent, discredited, erroneous or flawed, its data are said to be confounded or unreliable, or its findings are said to have failed to replicate or not been confirmed by later studies. Plain disagreement is NOT disputed: 'our results differ from [→9]', 'in contrast to [→9]', or reporting that the target itself found no effect.
- **neutral**: The text cites the target without saying anything against it.

## Question 2, use
- **specific**: The sentence rests on a finding of the target: a result, number, observation, or a method or protocol the authors took from it. Test: if the target's data had been made up, this sentence would lose its support. Includes 'X found that...', 'has been shown in mice [→7]', reported figures, 'as described in [→3]', 'consistent with [→9]', and one item in a list that carries the target alone.
- **counted**: This paper is a review or meta-analysis and the target is one of the studies it includes and analyses as data: counted ('two of the eight included trials [→9,10]'), pooled, or a row in a table of included studies. NOT a general summary table of the literature, NOT 'in line with earlier meta-analyses', NOT 'most of the literature uses X'.
- **background**: Textbook knowledge, a definition, a well-established mechanism, or a statement about a field, a need or an opinion. It would still stand if the target's data had been made up, even when only the target is cited.
- **described**: It says what the target did, proposed or studied (a method it used, a hypothesis it put forward, that a topic has been researched) without resting on its result.
- **unclear**: The text is garbled or too short to judge.

## Examples (invented):
- "miR-195 suppresses tumours in liver [4] and in breast cancer [→5]." -> neutral, specific
- "Mice lacking VDR in muscle develop sarcopenia [→8]." -> neutral, specific
- "Our results agree with those of Lee et al. [→11]." -> neutral, specific
- "Cells were treated as described previously [→6]." -> neutral, specific
- "Inflammation drives many chronic diseases [→3]." -> neutral, background
- "Nrf2 regulates antioxidant genes such as HMOX1 and NQO1 [→2]." -> neutral, background
- "There is a need for cheaper diagnostic kits [→4]." -> neutral, background
- "Two explanations have been proposed: the heterogeneity and the individual-risk hypotheses [→5]." -> neutral, described
- "Smith et al. [→7] used a random forest to classify the images." -> neutral, described
- "Of the eight included trials, two enrolled only women [→9,10]." -> neutral, counted
- "Table of included studies: Iwamoto 2008 [→37] | Yonsei Med J | 12 months" -> neutral, counted
- "Our findings agree with earlier meta-analyses [5, →7]." -> neutral, specific
- "A later investigation found the data in [→8] were fabricated." -> disputed
- "Some data discussed in that review have since been retracted [→12]." -> disputed
- "Deleting ten toxin genes cut persister numbers [→14]. These data were later found to be confounded by phage contamination [15]." -> disputed
- "XMRV was detected in patients with chronic fatigue [→2]. Later studies failed to confirm any association [4–11]." -> disputed
- "Our findings are inconsistent with those of earlier studies [4, →9]." -> neutral, perfunctory use
- "A Cochrane review found no benefit of antivirals [→12]." -> neutral, specific

## From answers to a label (fixed rule, applied by code)
The number of references sharing the target's citation group (n) is counted by code, not judged.
1. Formula markup instead of prose: *unclear*.
2. stance = disputed: *aware*.
3. use = counted, and the passage has a counting word (studies, trials, included, pooled, meta-analysis, cohorts,
   patients ...): *substantive*. Without such a word, counted is read as specific.
4. n >= 2 (cited together with other references): *perfunctory*.
5. use = specific: *substantive*. use = unclear: *unclear*. Otherwise: *perfunctory*.

Panel: majority of three models; *aware* if any model says disputed and the passage has a retraction, fraud or
image-integrity word, or if two models say disputed. A citing paper takes its strongest passage label
(aware > substantive > perfunctory > unclear).
