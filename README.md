<p align="center">
  <img src=".github/assets/banner.png" alt="SaneCite: the retraction census" width="100%">
</p>

<p align="center">
  <a href="https://doi.org/10.5281/zenodo.23358099"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.23358099.svg" alt="DOI 10.5281/zenodo.23358099"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-5CDBF2" alt="MIT license"></a>
  <a href="https://orcid.org/0009-0001-0250-5446"><img src="https://img.shields.io/badge/ORCID-0009--0001--0250--5446-A6CE39?logo=orcid&logoColor=white" alt="ORCID"></a>
  <a href="https://sanecite.com"><img src="https://img.shields.io/badge/results-sanecite.com-5CDBF2" alt="Results at sanecite.com"></a>
  <a href="https://github.com/sponsors/MrSaneApps"><img src="https://img.shields.io/badge/donate-sponsor-5CDBF2?logo=githubsponsors&logoColor=white" alt="Donate through GitHub Sponsors"></a>
</p>

When a paper is retracted, other papers keep citing it. This repository counts those citations, reads them, and asks
one question: does the citing paper still lean on the retracted result? Everything is here: the method (published
before the results), the code, every model answer and every label, so anyone can check or re-run it.

## What we found

| Figure | What it counts |
|---:|---|
| **262,998** | citations made after retraction, across the 51,414 retracted papers checked (OpenAlex, 16 Oct 2026) |
| **32,626** | of those papers (63%) were cited at least once after their retraction |
| **55,688** | citations read in full text (22,553 retracted biomedical papers, open-access citing papers in Europe PMC) |
| **40.7%** | of the citations judged (21,037 of 51,626) use the retracted result as support |
| **3.3%** | say the cited paper was retracted |

<p align="center"><img src=".github/assets/chart.png" alt="Share of citations that use the retracted result as support: 43.6% one to two years after retraction, 39.1% at three to five years, 37.4% at six to ten years, 34.9% after eleven or more years. Share that say it was retracted: 2.7%, 3.4%, 3.8% and 6.3%." width="100%"></p>

**How sure are we?**
- The Phase 2 labels come from a panel of three AI models. On 150 citations labelled blind by a separate AI model
  (Claude), the panel caught 96.5% of the supporting citations, with a false-positive rate of 6.5%. Adjusting for
  that error gives 38.1% (95% CI 33.5-41.8%). A round of human labelling is next, and every figure is provisional
  until it is done.
- A citation-level audit of the 262,998 (200 random draws, checked against each citing paper's own reference list)
  found about 96.5% to be real citations. The rest were wrong links, retraction notices or duplicate records. So
  about 254,000 (247,000-260,000) are real citations.
- A citation is a flag, not a verdict. Every author named in our reports is asked to respond before publication.

## Support this work

SaneCite is an independent research project. Reading a citation costs fractions of a cent; the expensive part is
experts checking the machine's calls, and that is what funding pays for.

- **Donate:** [github.com/sponsors/MrSaneApps](https://github.com/sponsors/MrSaneApps), one-time or monthly.
- **Pledge:** [sanecite.com/donate](https://sanecite.com/donate). Pledges are not binding while a nonprofit fiscal
  sponsor is finalized; pledgers hear first when that giving opens. Gifts are not tax-deductible yet.
- **Foundations, publishers and institutions:** to fund the human check, a research partnership or an audit of your
  own field, write to [hi@saneapps.com](mailto:hi@saneapps.com).
- **Free ways to help:** cite the dataset, re-run the code, and
  [open an issue](https://github.com/MrSaneApps/sanecite-retraction-census/issues) for any error you find. We
  correct mistakes in public.

Every gift and every spend will be published, with what it paid for.

## What's in this repository

| Path | What it is |
|---|---|
| [`PROTOCOL.md`](PROTOCOL.md) | The analysis plan, registered before the final analysis, with every dated amendment |
| [`codebook.md`](codebook.md) | The questions the models answer and the rules that turn answers into labels |
| [`phase1/`](phase1/) | Phase 1: the count of citations made after retraction (Retraction Watch, Crossref, OpenAlex) |
| [`scripts/`](scripts/) | Phase 2: build the frame, extract citing passages, label them, analyse |
| [`data/`](data/) | The census: frame, every citing passage, each model's answer, final labels, results |
| [`validation/`](validation/) | Blind answer keys and scores for the model panel |
| [`human_labels/`](human_labels/) | The human labelling round: draw and instructions, scoring fixed in advance |
| [`MANIFEST.sha256`](MANIFEST.sha256) | Hashes that fix each file at the date it was registered |

**Data files** (`data/`): `stage1_papers.jsonl.gz` (the 22,553 retracted papers, with Retraction Watch reason, dates
and later-citation counts), `stage2_v31.jsonl.gz` (every extracted citing passage), `stage3_{jev,clef,gemma}.jsonl.gz`
(each model's answer per passage), `census_rows.jsonl.gz` (the label per citing pair), `citer_meta.jsonl.gz` (Europe
PMC metadata for all 130,315 later citations), `paper_numbers.md` (every figure quoted) and the result files. Citing
passages are short quotations from open-access papers, included so each label can be checked against its text.
Hsiao and Schneider's data are not redistributed here (Illinois Data Bank, doi:10.13012/B2IDB-8255619_V2).

## Re-run it

Re-create the published results from the released data (about a minute, no accounts needed):

```sh
mkdir work
for f in data/*.gz; do gunzip -c "$f" > "work/$(basename "${f%.gz}")"; done
cp validation/* work/
SANECITE_DATA=work python3 scripts/analyze_census.py
```

`work/census_results.json` matches `data/census_results.json`. Other analyses are listed in `PROTOCOL.md`.

- **Phase 1 count:** see [`phase1/README.md`](phase1/README.md). It needs the Retraction Watch file from Crossref
  Labs and, for a full run, an OpenAlex API key.
- **Re-label citations with the models:** `scripts/stage3_census.py` through `scripts/model_calls.py`. It needs a
  Cloudflare account (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`).

## Cite

Joseph, S. (2026). *SaneCite retraction census: post-retraction citations to 22,553 retracted biomedical papers
(protocol, code and data)*. Zenodo. https://doi.org/10.5281/zenodo.23358099

This DOI always points to the latest version; each version also has its own DOI on Zenodo. GitHub's "Cite this
repository" button uses [`CITATION.cff`](CITATION.cff).

## History

- **13 Oct 2026:** protocol registered before the final analysis.
- **14 Oct 2026:** census data released (amendment 3); human labelling scoring fixed before any answers exist
  (amendment 4).
- **15 Oct 2026:** rates reported as counts over totals to fix a rounding error (headline 40.7%, not 40.8%).
- **16 Oct 2026:** all code released (amendment 5, version 1.1.0). The Phase 1 count now leaves out administrative
  retractions, the rule Phase 2 always used (262,998, down from 286,050).

## Contact and license

Stephan Joseph, SaneApps, Dahlonega, Georgia · [hi@saneapps.com](mailto:hi@saneapps.com) ·
[ORCID 0009-0001-0250-5446](https://orcid.org/0009-0001-0250-5446) · [sanecite.com](https://sanecite.com)

Code and data under the [MIT license](LICENSE). AI use: language models produce the labels, and Claude (Anthropic)
wrote most of the code; see `PROTOCOL.md`.
