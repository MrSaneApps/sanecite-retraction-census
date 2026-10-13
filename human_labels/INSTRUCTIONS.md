# Labelling instructions (SaneCite census, human check)

Thank you for helping. You will read about 250 short passages from scientific papers. In each passage one reference,
the "target", is marked with an arrow →. Answer two questions per passage in `passages.csv`.

Please work alone, do not discuss items with the other labeller, and do not look up the cited papers or their status.
If a passage has several numbered rows (passage 1, 2, 3), they come from the same citing paper; answer each row.

## Q1_disputed: does the text say anything against the target? (yes / no)
- **yes**: Anywhere in the TEXT, including the sentences before and after the citation, or in the section heading, the target itself is called retracted, withdrawn, fraudulent, discredited, erroneous or flawed, its data are said to be confounded or unreliable, or its findings are said to have failed to replicate or not been confirmed by later studies. Plain disagreement is NOT disputed: 'our results differ from [→9]', 'in contrast to [→9]', or reporting that the target itself found no effect.
- **no**: The text cites the target without saying anything against it.

## Q2_use: how does the sentence use the target? (specific / counted / background / described / unclear)
- **specific**: The sentence rests on a finding of the target: a result, number, observation, or a method or protocol the authors took from it. Test: if the target's data had been made up, this sentence would lose its support. Includes 'X found that...', 'has been shown in mice [→7]', reported figures, 'as described in [→3]', 'consistent with [→9]', and one item in a list that carries the target alone.
- **counted**: This paper is a review or meta-analysis and the target is one of the studies it includes and analyses as data: counted ('two of the eight included trials [→9,10]'), pooled, or a row in a table of included studies. NOT a general summary table of the literature, NOT 'in line with earlier meta-analyses', NOT 'most of the literature uses X'.
- **background**: Textbook knowledge, a definition, a well-established mechanism, or a statement about a field, a need or an opinion. It would still stand if the target's data had been made up, even when only the target is cited.
- **described**: It says what the target did, proposed or studied (a method it used, a hypothesis it put forward, that a topic has been researched) without resting on its result.
- **unclear**: The text is garbled or too short to judge.

## Examples (invented):
- "miR-195 suppresses tumours in liver [4] and in breast cancer [→5]." -> no, specific
- "Mice lacking VDR in muscle develop sarcopenia [→8]." -> no, specific
- "Our results agree with those of Lee et al. [→11]." -> no, specific
- "Cells were treated as described previously [→6]." -> no, specific
- "Inflammation drives many chronic diseases [→3]." -> no, background
- "Nrf2 regulates antioxidant genes such as HMOX1 and NQO1 [→2]." -> no, background
- "There is a need for cheaper diagnostic kits [→4]." -> no, background
- "Two explanations have been proposed: the heterogeneity and the individual-risk hypotheses [→5]." -> no, described
- "Smith et al. [→7] used a random forest to classify the images." -> no, described
- "Of the eight included trials, two enrolled only women [→9,10]." -> no, counted
- "Table of included studies: Iwamoto 2008 [→37] | Yonsei Med J | 12 months" -> no, counted
- "Our findings agree with earlier meta-analyses [5, →7]." -> no, specific
- "A later investigation found the data in [→8] were fabricated." -> yes
- "Some data discussed in that review have since been retracted [→12]." -> yes
- "Deleting ten toxin genes cut persister numbers [→14]. These data were later found to be confounded by phage contamination [15]." -> yes
- "XMRV was detected in patients with chronic fatigue [→2]. Later studies failed to confirm any association [4–11]." -> yes
- "Our findings are inconsistent with those of earlier studies [4, →9]." -> no, background
- "A Cochrane review found no benefit of antivirals [→12]." -> no, specific

You do not need to count how many references share the citation; that is done by computer. Use the notes column for
anything that made a passage hard. Expect about 3 to 4 hours in total.
