# Positioning and precedents

The useful question is descriptive: **what observable engineering properties do
recovered research-code deposits have, and how much of that profile can a cheap
static instrument measure?** This does not require treating those properties as
proxies for valid estimates. A subsequent study could validate selected properties
against blinded comprehension or change tasks, but that is a separate estimand.

The contribution is a transparent corpus measurement: pinned deposit units,
source-role uncertainty, denominators and failure coverage across R, Python and
Stata. Neither duplication detection nor code-quality measurement is new.

| Precedent | Relationship to this instrument |
|---|---|
| [Trisovic et al. (2022), *A large-scale study on research code quality and execution*](https://pmc.ncbi.nlm.nih.gov/articles/PMC8861064/) | A close corpus precedent using Harvard Dataverse replication deposits and R code, with execution and code-cleaning analyses. This project focuses on prespecified static properties and includes Stata/Python; it should not claim to be the first large-scale research-code quality study. |
| [Pimentel et al. (2021), *Understanding and improving the quality and reproducibility of Jupyter notebooks*](https://pubmed.ncbi.nlm.nih.gov/33994841/) | A close notebook quality/reproducibility precedent. Notebook quality assessment is established work; this project's unit is the research deposit, with cell boundaries and incomplete coverage retained. |
| [PMD Copy/Paste Detector](https://pmd.github.io/pmd/pmd_userdocs_cpd.html) | Token thresholds and optional identifier/literal normalization are established clone-detection ideas. Here, the estimand is deposit-level union coverage with explicit source boundaries and recovery denominators. |
| [Good enough practices in scientific computing](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005510) | Practical guidance motivates organization and reducing repeated code. Recommendations do not by themselves validate a numeric quality scale. |
| [Best Practices for Scientific Computing](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.1001745) | Covers much more than static source properties, including workflow and testing. This instrument observes only a limited subset. |
| [Ten simple rules for making research software more robust](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1005412) | Environment and portability concerns motivate separate evidence indicators; static evidence cannot establish that software runs elsewhere. |
| [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) | A broad product-quality model, not the validation source for this project's thresholds or an ISO-compliance claim. |
| [Softverse](https://github.com/recite/softverse) | Supplies recovered files, language/container metadata and environment evidence. Its analysis-set deduplication is unsuitable for a within-deposit duplication denominator, so eligibility is reconstructed. |

The 50-token primary threshold is a declared operational choice, accompanied by
30/100-token sensitivity. It is not a literature-established boundary between good
and bad code. Identifier/literal normalization can produce broad structural
matches; incremental coverage is reported separately rather than called semantic
duplication.

Implementation references: [Python AST](https://docs.python.org/3/library/ast.html),
[Stata comments](https://www.stata.com/manuals/pcomments.pdf),
[Stata delimiters](https://www.stata.com/manuals/pdelimit.pdf), and
[Arrow Parquet](https://arrow.apache.org/docs/python/parquet.html). The scanner
uses standard language parsers where available, with an explicitly narrower
lexical instrument for Stata.

## Why duplication is a separate observation

Empirical clone studies do not justify treating every repeated token as lost
maintainability. [*On the Relationship of Inconsistent Software Clones and Faults*](https://arxiv.org/abs/1611.08005)
examines inconsistent clones and faults and reports only a weak relationship
between clone length and faultiness. This is a different measurement from the
static prevalence of duplicated text. The profile therefore separates exact
coverage, normalized candidates and source-role uncertainty without estimating
bugs or refactoring benefits.

Recent work also treats research-software problems as broader than source style:
[*The Nature of Technical Debt in Research Software*](https://arxiv.org/abs/2603.20415)
combines code-comment analysis with interviews. That supports treating this
scanner as one source of evidence, with a deliberately limited construct. It
does not supply validated weights for a composite score.
