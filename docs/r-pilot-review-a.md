# Independent R pilot diagnostic review A

Date: 2026-10-31. Reviewer: Codex AI reviewer A; the exact runtime model identifier was not exposed to this reviewer. This is an AI diagnostic review, not human validation, a precision estimate, or certification that the research results are correct.

## Selection and method

The coordinator froze the eight development packet prefixes below while pilot generation continued. Each identifies one JSON in `build/r-pilot-v1/review/`; all eight packets have `phase: development`. I read the full `source` of every selected packet, using numbered lines and rereading portions truncated in initial output. All sources begin at line 1, column 1, so the evidence locations below are source line numbers. No deposited code was executed. I did not read native analyzer outputs, extracted metrics, automated findings, or the other review. An additional packet was incidentally displayed during initial selection before the frozen list was applied; it is excluded from this report.

The selected units come from four deposits and are not an independent random sample. I looked for an identifiable failure mechanism, distinguished assumptions from observed code, and retained ambiguous cases as uncertain. Absence of an identified defect means only that this reading found none. Data, papers, original environments, and sourced helper files were not reviewed. Official R documentation was consulted to check the numeric-indexing mechanism described below.

| Packet prefix | Unit UID | Deposit | Lines | Overall classification |
| --- | --- | --- | ---: | --- |
| `0062ecaa` | `7e000c44213956669290d7ff9c4cd2af` | `doi:10.7910/DVN/26570` | 155 | no-identified-defect |
| `01701988` | `b89e4dfffeca56c79ce33c026a8f1c3d` | `doi:10.7910/DVN/E5IBHO` | 315 | defect-candidate |
| `0319a545` | `9a3f1e42c12959369dafaeb870e646e7` | `doi:10.7910/DVN/26570` | 82 | uncertain |
| `0525aac5` | `62894c75e8e3557bb86f01257f104890` | `doi:10.7910/DVN/E5IBHO` | 138 | no-identified-defect |
| `05d32b17` | `e740de4897575cc79924d9dbb5c02fa9` | `doi:10.7910/DVN/E5IBHO` | 149 | defect-candidate |
| `07e76e1e` | `b7f8db891a6c5e53ac5938b5bde0b0ff` | `doi:10.7910/DVN/8ODIRK` | 151 | uncertain |
| `0934ac37` | `01b55647f45f53e583748936eef4ac77` | `zenodo:6491871` | 82 | no-identified-defect |
| `0b1104b6` | `140bac7caa0853a986f48b7c52b49b6a` | `doi:10.7910/DVN/26570` | 77 | no-identified-defect |

## Findings by unit

### `7e000c44213956669290d7ff9c4cd2af`

**Classification: no-identified-defect. Confidence: moderate within the supplied source.** The fixed year sequence at line 55 makes the `1:length(yr)` loop at line 70 nonempty; its syntax alone is not evidence of an empty-sequence bug. Repeated model terms at lines 24 and 40 do not establish that the fitted model is incorrect. The result construction and simulated contrasts appear internally consistent.

The simulations at lines 106, 108, and 110 have no local seed declaration. This is an **uncertain** reproducibility concern, not a demonstrated computational defect: a caller could set the seed, and the intended tolerance for Monte Carlo variation is unknown. Missing context: the dataset, Zelig version, caller, seed policy, and target figure.

### `b89e4dfffeca56c79ce33c026a8f1c3d`

**Classification: defect-candidate. Confidence: high.** Line 218 calls `dwplot(m100)`, but the source defines `d100` at lines 209–211 and never defines `m100`. Line 3 clears the workspace, further weakening an explanation based on a preexisting interactive object. Under ordinary sequential execution with the intended packages, evaluating the argument fails with an object-not-found error and prevents the subsequent figure export beginning at line 281.

Missing context: the intended plot model and whether the deposited script was actually run sequentially. Imported package environments were not inspected. The likely nearby replacement is `d100`, but that intention needs confirmation. This is evidence about script execution, not evidence that the published estimates are wrong.

### `9a3f1e42c12959369dafaeb870e646e7`

**Classification: uncertain. Confidence: high in the inconsistency, moderate that it indicates an implementation error.** Line 2 describes a table with the number of male candidates as the dependent variable, whereas all four models at lines 20, 23, 26, and 29 use `n.women.cand`. The coefficient labels also describe women at lines 38–72. If the header states the intended analysis, this estimates the wrong outcome; if the header is stale, the calculations may be intentional.

Missing context: Table SI3, the intended artifact mapping, and variable definitions. Source text alone cannot distinguish an incorrect model from an incorrect comment.

### `62894c75e8e3557bb86f01257f104890`

**Classification: no-identified-defect. Confidence: limited by unavailable input data.** The source explicitly says it requires withheld tower coordinates at line 4. The merge at line 36 and treatment recoding at line 53 cannot be verified without those inputs. Line 56 evaluates a treatment-total equality, and line 59 says it should be true, but the expression does not enforce it. This is an **uncertain** check-strength concern: failure could go unnoticed in unattended execution, while an interactive author could inspect the result intentionally. There is no evidence here that the equality actually fails.

Missing context: join-key uniqueness, treatment totals, input schemas, and the intended interactive workflow. The regression's `month_year` column need not be created locally if supplied in the input; its use alone does not prove an undefined-variable defect.

### `e740de4897575cc79924d9dbb5c02fa9`

**Classification: defect-candidate. Confidence: high.** Lines 102–108 explicitly construct numeric `lat` and `lon`. The helper at lines 120–123 hashes unique input values, then returns `unname(unq_hashes[x])`. Line 125 includes both numeric columns in `cols_to_mask`, and line 129 applies the helper to them. For numeric `x`, the subscript selects positions; it does not look up each original coordinate's hash. Fractional coordinates become truncated integer positions, out-of-range positions yield missing values, and negative or mixed-sign indices can produce different behavior or errors. Distinct coordinate values can consequently receive the same unrelated hash or fail to produce the intended output.

This interpretation follows R's [extraction semantics](https://stat.ethz.ch/R-manual/R-devel/library/base/html/Extract.html) and [apply-family naming behavior](https://stat.ethz.ch/R-manual/R-devel/library/base/html/lapply.html). `USE.NAMES=TRUE` does not turn numeric indexing into value matching. The defect concerns mapping values to hashes; collision resistance is a separate question.

Missing context: actual coordinates, resulting vector dimensions, and any manually corrected output. Those determine the observed damage, but the numeric-coordinate call path is visible in the source. The header states that coordinate inputs are unavailable, so no empirical consequence was checked.

### `b7f8db891a6c5e53ac5938b5bde0b0ff`

**Classification: uncertain. Confidence: high that the transformations occur; low to moderate that they are erroneous.** Line 64 replaces all zeros in `ws_final` with missing values. Line 109 clips all negative values in the correlation frame to zero. If zero and negative scores are legitimate positions, these operations discard information or create rank ties before the Spearman correlations at lines 113 and 116. They may instead implement a documented scale or missing-value convention.

Line 111 performs complete-case deletion across both dimensions before either correlation, so missingness in one dimension can exclude an otherwise usable pair in the other. That may be a deliberate common-sample comparison. Lines 91–103 pair `soci_einstufung_*` perceptions with `immi_*` scores; the naming mismatch may reflect an intended cultural/immigration construct and is not sufficient to declare a wrong-variable defect.

Missing context: score ranges, missing-value codes, survey constructs, intended samples, and the helpers sourced at lines 10–11. These uncertainties prevent a concrete correctness judgment.

### `01b55647f45f53e583748936eef4ac77`

**Classification: no-identified-defect. Confidence: moderate within the supplied source.** The three readability transformations, identifier renaming, scale reversal, and exports appear consistent across their respective inputs. Package installation at lines 15 and 22 without local version pins raises an **uncertain** environment-reconstruction concern, but this source does not demonstrate that a version change alters results. Missing context: database schemas, input text encoding, readability package versions, and an external environment lockfile. No execution or output comparison was attempted.

### `140bac7caa0853a986f48b7c52b49b6a`

**Classification: no-identified-defect. Confidence: moderate within the supplied source.** Line 15 constructs the new-male-candidate outcome by subtracting previously elected male candidates. Models at lines 22, 25, and 28 distinguish the full sample and two subgroups. Although three models are estimated, the two labels at line 75 match the two models actually passed to `texreg` at line 77. Omitting `out.2` is not itself a defect: the table may intentionally show only the full sample and the positive subgroup.

Missing context: the target Table SI6/Table A4, intended model selection, and whether the input counts satisfy the outcome definition. Static reading cannot validate those substantive assumptions.

## Separate holdout diagnostic review

Date: 2026-10-31; same reviewer and limitations as above. The coordinator selected the first four lexically sorted holdout packets of at most 250 lines available at selection time and froze the prefixes below in `build/r-pilot-final/review/`. This is a convenience diagnostic sample, not an accuracy estimate. I read the entire supplied source of all four, without executing it or reading native findings or the other review. These observations are retained as holdout diagnostics; they are not tuning instructions or evidence validating a detector. The development review above is unchanged.

| Packet prefix | Unit UID | Deposit | Supplied lines | Overall classification |
| --- | --- | --- | ---: | --- |
| `010602e0` | `8ed9919200e05ad9982c4d8af6cab539` | `doi:10.7910/DVN/UQ5R7L` | 100 | defect-candidate |
| `01836577` | `84e8b1b388085f5ab467a114512386b2:chunk:2` | `doi:10.7910/DVN/ADIJN6` | 3 | no-identified-defect |
| `01bfd153` | `71c2004059385112add399e856f9f5a8` | `zenodo:5896606` | 47 | uncertain |
| `08645ac1` | `3b2b5c1baa5155eaba933f0203e50a01` | `doi:10.7910/DVN/OAJJIY` | 127 | uncertain |

### `8ed9919200e05ad9982c4d8af6cab539`

**Classification: defect-candidate. Confidence: high for the stated invocation condition.** Lines 29–36 extract the script filename from command arguments. Line 42 assumes that splitting this string at a directory separator produces a second element. For a basename-only argument such as `--file=script.R`, no separator matches, so the split has only one element; selecting `[2]` supplies a missing value to the path calculation. Consequently `setwd(pathName)` at line 45 cannot establish the directory. This is a conditional execution defect for an ordinary relative-filename invocation, not evidence that the authors' invocation failed. R documents the no-match behavior of [strsplit](https://stat.ethz.ch/R-manual/R-devel/library/base/html/strsplit.html). Missing context: the actual invocation and any documented requirement to use a full or directory-qualified path. The RStudio fallback may supply such a path and avoid this case.

**Additional classification: uncertain. Confidence: moderate.** Lines 87–90 group by `pubDateTime` and calculate counts per distinct value, then label the resulting summaries “Daily Average,” “Daily Min,” and “Daily Max” at line 94. If this column contains times within days, these are timestamp-level counts rather than daily totals. Even if it contains dates, days without articles are absent unless the input includes them. Missing context: the column's actual granularity and whether the intended denominator is all calendar days or only observed publication days. The column name alone does not establish a defective aggregation.

### `84e8b1b388085f5ab467a114512386b2:chunk:2`

**Classification: no-identified-defect. Confidence: very limited by fragment scope.** The entire supplied source consists of two blank lines and `print(demographics, booktabs = TRUE, linesep = "")`. Packet-relative line 3 maps to original source line 381 because `first_line` is 379. The object may be created in earlier chunks, and the print arguments may be appropriate for its class. Treating `demographics` as undefined merely because this chunk does not define it would be unjustified. Missing context: preceding chunks, object class, and print-method dispatch. This review does not cover the containing document.

### `71c2004059385112add399e856f9f5a8`

**Classification: uncertain. Confidence: moderate in the dependence on input contracts; low that these contracts are violated.** Lines 8–9 split `mydata_all` by `N_product`; lines 33 and 35 feed `voting_long_list[[i]]$share` and the corresponding split's `d` to the optimization model by position. No local key comparison establishes that the two lists use the same group and row ordering. If constructed differently upstream, the function could solve a model with mismatched shares and costs; it may instead rely on a valid caller invariant.

The `1:N_iter` loop at line 12 also assumes a nonempty set of groups, and `1:N_sim` at line 30 assumes a positive simulation count. An empty-group or zero-simulation call would not create an empty index sequence, but the source does not show such a call or promise those inputs are supported. Lines 38–40 solve and immediately read a variable without a visible status check; the external API may already signal failure. Missing context: caller constraints, input-list construction, the AMPL model file, solver status behavior, and the intended output ordering. No AMPL API failure is asserted.

### `3b2b5c1baa5155eaba933f0203e50a01`

**Classification: uncertain. Confidence: high in the visible sample restriction, low to moderate that it is unintended.** Lines 16–23 select a broad variable set and drop every row missing any selected variable. The fitted model at lines 26–32 uses a smaller set. Missing values in additional variables such as `women_genwinner`, `quality`, or `ltotal_spending` can therefore exclude observations that have every model variable observed. This changes the estimation sample if such missingness exists, but a shared complete-case sample across related models may be intentional. Missing context: missingness patterns, the analysis protocol, and the other reported models.

Line 13 reads from an author's absolute local path. This is a concrete portability dependency; it is not evidence of an incorrect estimate in the author's environment. The bootstrap is locally seeded at line 9. The two prediction grids at lines 53–69 and 76–92 intentionally differ in incumbency and otherwise appear consistent with the plotted comparison. Repeated grid construction alone does not demonstrate a copy-and-paste defect. Missing context also includes data coding, bootstrap convergence, and whether the predictor represents an estimated quantity whose uncertainty is handled elsewhere.
