# Unified code-quality profile

The study describes readability, maintainability, implementation reliability,
reproducibility and portability in deposited research code. These attributes
motivate indicators through explicit mechanisms: easier inspection, fewer
coordinated edits, explicit checks, reconstructable environments and fewer
machine-specific assumptions. The study does not estimate correctness or
successful reproduction, and it produces no aggregate quality score.

## One pipeline and dictionary

`assess` produces baseline measurements and, when configured, native R evidence
in the same run. `report` uses the run's frozen dictionary. There is one
[metric registry](../src/not_to_code/metrics.json), one deposit-metric schema and
one summarizer for languages, eligibility variants and subgroups. The separate
`r-pilot` and `r-profile` commands have been removed. Earlier outputs remain
historical artifacts; the v2 implementation requires a fresh output directory.

```sh
npm ci --prefix tools/r-analysis --ignore-scripts
Rscript --vanilla -e 'install.packages("renv", repos="https://cloud.r-project.org")'
Rscript --vanilla -e 'renv::restore(lockfile="tools/r-analysis/renv.lock", library="tools/r-analysis/library", prompt=FALSE)'
not-to-code assess --softverse-root ../softverse --output build/profile-v2 --language r --r-tools tools/r-analysis --recover-release --limit-deposits 60 --workers 4
not-to-code report --input build/profile-v2
```

Omit `--language` for all three supported languages. Omit `--r-tools` to run only
the baseline instrument; native R measures then explicitly say `not_measured`.
The language filter includes notebook and literate files as candidates, including
container-only deposits. Language is resolved on extraction; unknown or unsupported
units remain in the ledger, and candidate selection is not a guarantee that a
deposit contains that language. An optional `--deposit-list` accepts a JSON list
of dataset-version IDs within the eligible frame for a fixed comparison cohort.

`--recover-release` restores missing sources only when the release declares exact
content and reconstructed bytes match the original inventory hash. Existing
sources with changed hashes are not replaced. Missing sources stay missing.
Metadata uses frame disciplines and release deposit years, with unknowns retained.
Native runtimes and dependency locks are checked before analysis. Deposited code,
imports and project configurations are never executed. External analyzers have a
35-second timeout and flowR has a 512 MiB V8 heap limit, not a total-RSS limit.

## Measures retained, demoted and removed

| Treatment | Measures | Reason |
| --- | --- | --- |
| Indicators | Exact duplication, function length, nesting, selected formatting conventions, duplicate-argument and NA-comparison candidates, flowR absolute paths | A specific interpretation and detection scope can be stated |
| Evidence | Environment declarations, version constraints, locks and interpreter versions; recognized stopifnot assertions; conditional seed-call gap | Presence is informative but does not establish adequacy or execution |
| Sensitivity | 30/50/100-token thresholds; within/between-file coverage; additional normalized matches; both eligibility variants | The conclusions should not depend silently on one threshold or provenance assumption |
| Context | Files, code lines, tokens, file concentration, routine/control counts, code outside routines, working-directory changes and bundled dependencies | These describe project/task composition rather than an ordering from bad to good |
| Removed from profile | Lexical absolute-path guesses, broad path-like literals, trailing whitespace and mixed-tab counts; lintr sequence/length/vector-logic advice | Ambiguous argument roles, weak relevance, duplicate conventions or mixed efficiency/correctness interpretations |

Legacy lexical findings remain raw diagnostic evidence, not profile metrics.
R formatting uses the selected native lintr rules. Python/Stata retain the
explicit code-line-length convention, with no claim of interchangeable scores
across languages. Package age and a general "tests present" score are not added:
the first needs historical dependency/version information, and the second needs
a defined catalog and cannot stand for adequate tests.

## Denominators and sensitivity

Each deposit contributes once per language and eligibility variant. Every metric
retains numerator, denominator, eligible/measured unit counts and status. Each
registry entry records its attribute, role, rationale, operational definition,
units, producer, supported languages and limits.

Primary distributions use complete measurements; partial results are separately
exported. `inventory_only` is a separate population for environment evidence.
`missing`, `unsupported`, `not_measured` and `inapplicable` are never zeros. Lint
densities use only units with both successful linting and code-line measurement.
A failure of flowR's path feature does not discard successful call analysis.

The `exclude_uncertain` variant filters the same source units for baseline and
native measurements. Both variants have their own population summaries. A paired
sensitivity table separately restricts to deposits complete under both variants
and reports the median within-deposit change. It does not confuse changing
population composition with a change in the measurement of the same deposits.
Environment flags retain their independent recovered-inventory scope.

Exact duplication counts originals and copies in nonoverlapping matches, with
union coverage to avoid double counting. Within/between-file fractions cannot be
added. Normalized additional coverage replaces names/literals and is a broad
structural match, not semantic equivalence. Code outside functions is context;
linear scripts can be appropriate.

## Environment and randomness limits

Environment extraction uses Softverse's supported records from renv locks,
DESCRIPTION, requirements files and notebook metadata. Records preserve source
identities and vendored status; some describe bundled packages. `environment.json`
separately lists filename evidence for uv, Poetry, Pipenv, packrat, Conda and other
artifacts. Filenames do not establish valid contents or use. Free-text session
information and unsupported formats are not comprehensively measured.

The randomness catalog covers base sampling, selected stats random generators,
base `set.seed`, withr seed helpers and parallel `clusterSetRNGStream`. It uses
flowR call resolution, namespace/alias handling and R argument matching. RNG
configuration is recorded separately from seed-setting calls. Among completely
processed deposits with recognized stochastic calls, the indicator counts those
with no recognized seed-setting call with a supplied non-NULL expression.

Numeric literals, NULL, omitted arguments and unresolved expressions remain
separate in native evidence. A supplied expression may change across runs or
resolve to NULL; its presence does not establish an effective seed. The detector
does not link seed calls to stochastic operations across files, establish execution
order, validate seed values, or comprehensively cover model-fitting APIs and RNG
state restoration. A seed after a stochastic call still counts as deposit-level
presence. Other assertion/test frameworks are outside the stopifnot indicator.

API references: [flowR call-context](https://github.com/flowr-analysis/flowr/blob/main/src/queries/catalog/call-context-query/call-context-query-format.ts),
[R RNG](https://stat.ethz.ch/R-manual/R-devel/library/base/html/Random.html),
[withr](https://withr.r-lib.org/reference/with_seed.html),
[parallel RNG](https://stat.ethz.ch/R-manual/R-devel/library/parallel/html/RngStream.html).

## Reporting and comparison

The HTML report shows distributions, both eligibility variants, paired
sensitivity, context and all clone thresholds. Definitions expand beside results;
raw evidence stays in linked outputs. CSVs contain every measure by collection,
discipline, deposit year and five-year period. Subgroups with fewer than five
complete observations retain counts but no HTML estimate. This is a display
rule, not a precision guarantee. Dates describe deposits, not when code was
written. Current discipline labels are often too broad for substantive comparisons.

`metrics.parquet` and `native.parquet` hold measurements and native evidence.
Native locations are unit-relative, with original first-line/column and cell/chunk
identity alongside them; `ledger.parquet` supplies file paths and source status.
`dictionary.json`, `metadata.json`, `environment.json` and all measurement tables
are hashed in the assessment manifest. The report records its own renderer and
output hashes without changing the assessment's provenance.
