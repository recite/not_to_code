# R pilot independent diagnostic review B

Reviewed 2026-10-31 by a separately prompted Codex AI reviewer. The exact runtime
model identifier was not exposed to this reviewer. This is AI diagnostic review,
not independent human validation, a precision estimate, or a judgment about the
published papers' correctness.

The selection was frozen to the eight development packet prefixes below while
the pilot continued generating files. All 1,149 source lines were read; an initial
combined display was truncated, so the affected units and the second unit's tail
were read separately. No deposited code was executed. Native analyzer outputs,
aggregate metrics, findings, and the other reviewer's work were not inspected.
Only packet metadata and full source text were available; data, papers, upstream
scripts and historical package versions were not inspected. Source lines below
are file-relative because all eight packets have first_line=1 and no container.

## Frozen selection

| Packet prefix | Unit UID | Lines | Overall diagnostic classification |
|---|---|---:|---|
| 0062ecaa | 7e000c44213956669290d7ff9c4cd2af | 155 | no-identified-defect |
| 01701988 | b89e4dfffeca56c79ce33c026a8f1c3d | 315 | defect-candidate |
| 0319a545 | 9a3f1e42c12959369dafaeb870e646e7 | 82 | uncertain |
| 0525aac5 | 62894c75e8e3557bb86f01257f104890 | 138 | uncertain |
| 05d32b17 | e740de4897575cc79924d9dbb5c02fa9 | 149 | defect-candidate |
| 07e76e1e | b7f8db891a6c5e53ac5938b5bde0b0ff | 151 | uncertain |
| 0934ac37 | 01b55647f45f53e583748936eef4ac77 | 82 | no-identified-defect |
| 0b1104b6 | 140bac7caa0853a986f48b7c52b49b6a | 77 | no-identified-defect |

## Unit findings

**7e000c44213956669290d7ff9c4cd2af — no-identified-defect, moderate confidence
within the inspected source.** The repeated predictor
`n.women.cand.previously.elected` on lines 24 and 40 is redundant formula text,
not evidence that the covariate is fitted twice. The `1:length(yr)` loop at line
70 iterates a fixed, nonempty sequence defined at line 55; the generic empty-vector
edge case is not present in this source. Simulation calls at lines 106–110 have
no local seed setting, which creates reproducibility uncertainty but does not
establish a wrong estimator or result. The Zelig summary indexing at lines
113–131 needs the historical package version to verify its expected structure.
Long lines and repeated low/high scenarios are not themselves defect labels.

**b89e4dfffeca56c79ce33c026a8f1c3d — defect-candidate, high confidence.** Line
218 calls `dwplot(m100)`, but the unit defines `d100` at lines 209–211 and never
defines `m100`. It clears its workspace at line 3 and does not source another
script. Under ordinary package behavior this stops the script before the final
PNG is produced at lines 281–313. This is a concrete probable naming error;
execution was not attempted and package-side bindings were not checked.
Additional review note: the code plots four interaction estimates while one
additional interaction model is fitted, but the commented plotting code and
labels indicate intentional selection rather than a demonstrated defect.

**9a3f1e42c12959369dafaeb870e646e7 — uncertain, moderate confidence in the
mismatch, low confidence that the computation is wrong.** The header at line 2
claims a male-candidate dependent variable. All four formulas at lines 20, 23,
26 and 29 use `n.women.cand`, and their coefficient labels also say female.
This could be a stale header, a misnamed script, or the wrong table's code.
The paper's Table SI3 and the intended input/output mapping are required to
adjudicate it. Repeated model formulas with progressively different interactions
are intentional specifications on the face of the code, not independent bugs.

**62894c75e8e3557bb86f01257f104890 — uncertain, moderate confidence.** Lines
107–116 use `month_year` as a fixed effect, but the source only visibly creates
`day` and `year` at lines 74–79. It may arrive in either input CSV or the merge;
without input schemas this is not an undefined-variable defect. The diagnostic
comparison at line 56 only prints a logical value and does not enforce an
assertion. That is weak error detection, not evidence that the equality fails.
The header explicitly states that unavailable tower coordinates prevent running
this file (line 4); do not misclassify acknowledged restricted inputs as an
implementation mistake. Merge-key uniqueness and zero replacement require data
and design context before assigning a correctness label.

**e740de4897575cc79924d9dbb5c02fa9 — defect-candidate, high confidence in the
mechanism.** Lines 102–108 create numeric `lat` and `lon`. The helper at lines
120–123 applies `vapply(unique(x), ..., USE.NAMES=TRUE)` and then returns
`unq_hashes[x]`. The helper is applied to `lat` and `lon` at lines 125–129.
For numeric `x`, `USE.NAMES` does not create a mapping keyed by the numeric
values, and `[x]` performs positional numeric indexing. Consequently the
anonymization can select unrelated hashes, yield missing values or unsuitable
lengths, or fail for some numeric patterns. A value-to-unique-index mapping is
needed for numeric inputs. The published data and downstream impact have not
been checked. The official R documentation specifies that automatic names from
`USE.NAMES=TRUE` apply when X is character:
[R vapply documentation](https://stat.ethz.ch/R-manual/R-devel/library/base/html/lapply.html).
This finding concerns a source-level mechanism, not the adequacy of CRC32 for
privacy. As in the previous unit, the printed equality check at line 61 is not
an enforced assertion, and the source explicitly acknowledges missing private
coordinates at line 2.

**b7f8db891a6c5e53ac5938b5bde0b0ff — uncertain.** At lines 61–64, summed scores
of zero are all replaced with NA to represent absent observations. If true zero
scores are possible, this also removes valid values. Whether they occur depends
on the score scale and data. Confidence is high in the conditional mechanism,
but low in an actual data error. Lines 91–103 pair perceived `soci` values with
actual `immi` values. These may be intentional operationalizations of a cultural
dimension; the variable dictionary and paper are necessary to judge the pairing.
The negative-value clipping at line 109 is likewise an explicit analytical
choice whose justification cannot be determined from code alone. None of these
is labeled a confirmed defect. Repeated party-specific assignments are verbose
but visibly follow a consistent mapping.

**01b55647f45f53e583748936eef4ac77 — no-identified-defect, moderate confidence
within scope.** It deliberately installs unpinned GitHub packages at line 22,
so later runs may use changed implementations. This is environment/reproduction
evidence, not proof of incorrect readability scores. The complete-case filter
for article abstracts (line 42), absent from the NBER/full-text branches, could
be intentional sample handling; downstream use is needed to judge it. The
score negations and renamed columns are internally consistent with comments.
Database schema, API versions and the SQL selection's substantive adequacy were
not validated. No defect is inferred from the unclosed connection alone in this
short top-level script.

**140bac7caa0853a986f48b7c52b49b6a — no-identified-defect, moderate confidence
within scope.** The script defines three models but exports `out.1` and `out.3`
(line 77). The two model labels (line 75) match the exported pair, so omission
of `out.2` is not itself a defect. Whether this pair matches Table SI6 requires
the table. Construction of new-male-candidate counts (line 15) assumes sensible
input counts; nonnegativity and the Poisson specification cannot be validated
without data and the research design.

## Diagnostic implications

The two strongest candidates involve an undefined model name and a type-sensitive
lookup, rather than whitespace or a universal ban on repetition. The other
observations show why comments, data schemas, and the intended output are needed
for correctness labels. No-identified-defect means only that this review did
not identify a supported mechanism in the unit; it is not a clean bill of health.
The selection contains several units from the same deposits and is not an
independent sample of eight research projects. No prevalence, accuracy, or
structure–correctness association is estimated from it.

## Independent holdout diagnostic review

Reviewed 2026-10-31 by the same Codex AI reviewer; an exact runtime model
identifier was not exposed. This section preserves the development review above
and records a separate reading of four frozen holdout packets from
`build/r-pilot-final/review`. Selection was the first four lexically sorted
holdout packets with at most 250 source lines available at selection time.
This is a convenience diagnostic sample, not a random sample, human validation,
or an accuracy estimate. These observations were not used to tune checks or
claimed as validation of any subsequent tuning.

I read every line of each packet's source (277 lines total) and its identifying
metadata. I did not execute deposited code, inspect native analyzer outputs,
metrics or findings, or consult the other review. Line numbers below are
packet-relative unless explicitly stated. Full surrounding notebooks, data,
model files, papers and runtime environments were unavailable to this review.
No external API lookup was needed for the limited claims in this section.

| Frozen packet filename | Unit UID | Source lines | Classification |
| --- | --- | ---: | --- |
| `010602e05abcf8008d7d69ff86f0355b34351146d23629f7826487deed63f5f8.json` | `8ed9919200e05ad9982c4d8af6cab539` | 100 | uncertain |
| `018365773b070f487e31927556c0f2d5a0c369de8b59a6de5cc66e03c3ff3baf.json` | `84e8b1b388085f5ab467a114512386b2:chunk:2` | 3 | no-identified-defect |
| `01bfd1539e6c2730082385e68d8a9f4a2f9d1a592fd4c7ee9a172e093fff2029.json` | `71c2004059385112add399e856f9f5a8` | 47 | uncertain |
| `08645ac1a7fc6f09adda3c39bf698522a3d528da0af31b86790a2999849d8343.json` | `3b2b5c1baa5155eaba933f0203e50a01` | 127 | no-identified-defect |

**8ed9919200e05ad9982c4d8af6cab539 — uncertain.** Lines 87–90 count records by
`so_txt` and `pubDateTime`, then take the mean, minimum and maximum of those
counts. Line 94 labels these quantities “Daily Average”, “Daily Min” and
“Daily Max”. If `pubDateTime` contains intraday timestamps, the calculations
summarize timestamp groups, not days. If upstream preparation already
normalizes it to a date, that mechanism does not apply. Even with dates,
zero-article days are absent from the grouped counts, so the average and
minimum describe observed publication days unless the input already completes
the daily grid. Confidence is high in these conditional mechanisms, but low
that either is an actual defect: the input schema, date preprocessing and
intended denominator are missing. Line 63 also explicitly combines `rts.ch`
with `srf.ch`; this may intentionally combine related outlets and is not
independently classified as an erroneous recode. The personal-environment
fallback at line 34 affects how the script can be launched, not the newspaper
statistics themselves.

**84e8b1b388085f5ab467a114512386b2:chunk:2 — no-identified-defect, low confidence
beyond the three-line unit.** The only statement is
`print(demographics, booktabs = TRUE, linesep = "")` at local line 3
(original source line 381; the packet begins at line 379). The object is not
defined in this chunk, which is expected for a later notebook chunk and does
not demonstrate an undefined-object defect. Correctness depends on the earlier
creation and class of `demographics`, the applicable print method, and notebook
execution order. The supplied source does not support a more specific defect
claim; reviewing a tiny chunk is particularly weak evidence of correctness.

**71c2004059385112add399e856f9f5a8 — uncertain.** The function groups
`mydata_all` by `N_product` at line 8 and uses positional indexing into a
separately supplied `voting_long_list` at line 33. The supplied shares must
therefore have the same group order and within-group arrangement required by
the AMPL model. If the caller built the list in a different order, the function
can attach shares to the wrong problem; the source alone does not establish
such a mismatch. Confidence is high in the alignment assumption and low in an
actual defect. Missing context comprises the caller, the construction of both
inputs and `DC_dual_all.mod`. Likewise, `1:N_iter` at line 12 and `1:N_sim`
at line 30 require positive counts; an empty input would not produce an empty
iteration sequence. A valid nonempty-input contract would make this intentional
rather than a demonstrated bug. The solve-then-extract sequence at lines 38–40
contains no explicit success check, but without the solver/API behavior and
actual solve status I do not infer invalid results. No source changes are
proposed from this holdout observation.

**3b2b5c1baa5155eaba933f0203e50a01 — no-identified-defect, moderate confidence
within scope.** The two prediction scenarios differ intentionally on
`incumbent` (lines 53 and 76), and each plot uses the corresponding prediction
object (lines 102–110); visible repetition has not produced an evident
scenario mix-up. The broad complete-case restriction at lines 16–23 includes
variables absent from this model's formula (lines 26–32). This can exclude more
observations than model-specific complete-case filtering, but it may enforce
a shared analysis sample. Assessing that choice requires the data and paper.
The absolute input path at line 13 is a concrete portability dependency, not
proof that the model is wrongly estimated. The script sets a random seed at
line 9. I did not check bootstrap convergence, the input variables' meaning,
the provenance of `xbprimary`, or agreement with the manuscript. Absence of a
supported implementation defect in this reading does not resolve those issues.

No high-confidence defect candidate was identified in these four units. That
statement concerns this source reading alone and supplies neither a numerator
nor a denominator for native-tool detection accuracy. The context-dependent
observations remain unresolved; they must not be counted as confirmed defects
or treated as evidence that a native diagnostic is correct.
