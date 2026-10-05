# Engineering properties of deposited research code

Specification v1, 2026-10-04. This is a descriptive measurement study, not a
validation of scientific results or a causal study of programming practices.

## Construct and estimand

Engineering quality means properties relevant to understanding, modifying, and
relocating code. Our instrument records a **profile of observable properties**;
it does not estimate an independently validated latent quality or human effort.
Duplication and complexity can be appropriate. Formatting records compliance with
explicit conventions. No composite score, author ranking, or quality pass/fail is
constructed.

The primary estimand is the equal-deposit distribution of the prespecified static
properties below, separately for R, Python, and Stata, among recovered, eligible
deposit snapshots in a pinned Softverse journal-collection frame. The unit is
deposit × language. Each deposit contributes once within each language. We do
not pool these units into a cross-language ranking.

The time reference is the recovered snapshot, not publication time. A DOI must
map to one dataset-version identifier in an input run; ambiguous versions cause
an error rather than an arbitrary selection. Files must have unique identifiers.
Unavailable and unsupported material stays in the coverage ledger. The frame
does not represent all published research. Descriptive census summaries have no
sampling confidence intervals; measurement error and incomplete recovery remain.

## Inclusion

Use all inventoried source, rather than Softverse's analysis-set flag. Include
exact copies and code repeated across deposits. Exclude recognizable installed
dependency trees, OS metadata and notebook checkpoints. A `vendor` directory,
an `ado` directory, a package marker, a shared hash, or an old-looking filename
alone is insufficient to establish third-party authorship: classify such files
as uncertain. Include uncertain files in the primary candidate-code analysis and
exclude them in a reported sensitivity. The results concern **candidate analysis
code**, not established author-written code. Exclusions have named rules.

Analyze supported notebook cells and literate chunks separately, with cell/chunk
and original-line coordinates. No clone window crosses one of these boundaries.
Unsupported embedded code, magics and incomplete blocks are recorded. Static
analysis never executes the deposited scripts, their imports or configuration.

## Measurements

The packaged `metrics.json` is the executable dictionary used in reports. Values,
numerators, denominators, coverage counts and status are stored together.

* **DRY:** union coverage of code tokens participating in at least one exact
  contiguous match of 50 tokens with a distinct, nonoverlapping occurrence in
  the same deposit and language. Sensitivities use 30 and 100 tokens. Count both
  originals and copies; overlapping matching spans count once. Report within-file,
  between-file, and union coverage. All successfully tokenized code tokens,
  including short files, are in the denominator. Comments and presentation
  whitespace are removed. Python indentation and logical statement endings are
  structural tokens; R statement endings and Stata logical statement endings
  are retained. Token conventions differ across languages.
* **Structural matches:** replace identifier and literal values with typed
  placeholders. Report incremental coverage outside exact matches, not semantic
  equivalence or proof that a refactoring is desirable. Function names can also
  normalize, so these are deliberately broad candidates. No type-3 fuzzy or
  embedding-based semantic matching is claimed.
* **Structure:** counts of control-flow constructs and their maximum nesting,
  routine code-line lengths, routine counts, and fraction of code lines outside
  routines. Python counts if/conditional expressions, for/async-for, while,
  try/try-star and match; R counts if/for/while/repeat. Stata counts recognized
  if/else-if, foreach/forvalues/while and program blocks. Function/program
  boundaries reset control depth. Stata is lexical, not a complete syntax check.
  Dynamic commands and foreign blocks make Stata structural coverage partial.
  Nested routine spans are unioned for top-level line coverage.
* **Organization:** number of files, median file code lines, largest-file share,
  routine count and median routine length. No routine means routine length is
  inapplicable, not zero. Comments and blank lines are not code lines. Multiline
  strings containing data count as code; Python standalone docstrings do not.
* **Formatting:** counts and per-1,000-code-line rates of code lines over 100
  characters, trailing whitespace and mixed tabs/spaces in leading indentation.
  Comments-only lines are excluded. Long literals remain findings, not errors.
* **Portability:** recognized literal absolute filesystem paths in filesystem
  operations, other path-like string literals, and working-directory changes.
  POSIX, Windows drive and UNC paths are recognized. URLs are not filesystem
  paths. Dynamic path construction is not resolved. Directory changes are not
  automatically failures. Findings never claim referenced data are missing.
* **Environment:** observed dependency declarations, version constraints, locked
  dependencies, bundled dependencies and interpreter-version evidence, kept
  distinct. This is evidence within Softverse's recovered manifest inventory;
  zero means no such evidence was recorded, not that the environment is absent
  or reproducible. The tables cannot establish a complete dependency closure.

For a deposit metric, complete means all included source units eligible for that
metric were measured. Partial means at least one failed; missing means none were
measured. Unsupported and inapplicable are distinct. Token measurements may be
available when structural parsing fails. Zero findings never substitutes for a
tool failure. Primary aggregate medians, quartiles and binary prevalence use
complete units; partial estimates are separately summarized with coverage.
Counts are not compared across languages as interchangeable instruments.

## Validation and reporting

Fixtures cover lexical boundaries, clone overlaps, failures and source mapping.
Controlled transformations establish invariance to presentation whitespace and
comments, behavior after renaming, and the expected effect of adding a copy.
Validation samples use a stable hash ordering with a recorded seed, stratified
by language and findings, nonfindings, uncertain exclusions and parsing difficulty.
Inspect 30 files per language during development and a disjoint 30 per language
after fixes; retain labels and examples. These are diagnostic samples, not
population accuracy estimates. Changes prompted by inspection are documented.

Every output is linked to input/table hashes, tool versions and a run fingerprint.
A resumed run refuses changed measurement code or inputs. Source hash mismatches
are ledger failures. Tables and the report must reconcile with the ledger.

## Prior exposure and deviations

Before this specification we inspected the historical scripts, dependency tables,
Softverse schemas, metadata counts and three notebook paths. We tested the old
lint-summary function on synthetic examples. We had not computed the new quality
profile. This is a versioned, self-attested specification, not preregistration.

* Initial implementation: no deviation recorded.

## Implemented scope and audit amendments

The initial excerpt audit found R string escapes that resembled UNC paths before
unescaping; R literals are now decoded first. Whole Stata source units containing
Mata, Python, or rsource are withheld as partial rather than attributed wholly to
Stata. Macro-built commands retain lexical measurements but not structural ones.
Python syntax is interpreted by the recorded Python 3 runtime; Python 2 syntax
may retain token measurements while structural parsing fails. Only formal
module/class/function docstrings are excluded, not arbitrary string expressions.
Python f-string and template-string literal fragments retain whitespace in exact
tokens and receive typed placeholders in normalized tokens. Token boundaries can
differ across Python runtime versions, which are recorded in each run.

Notebook cells with absent language metadata remain unattributed; explicitly
declared unsupported languages retain their names in coverage. Cell magics can
identify a supported language independently. Literate chunks retain unsupported
engines and empty chunks; chunk-level `engine=` overrides remain unattributed
because the instrument does not evaluate those options.

Portability recognition is deliberately narrow: a literal in the first positional
argument of a listed Python/R filesystem-call spelling, or a quoted literal in
a listed Stata filesystem-command line. Names are not resolved to implementations;
Stata command-line recognition does not resolve option argument roles. Other
absolute-looking literals remain a separate broad category, including regexes,
URL suffixes, command flags and dynamic path fragments. Root-only `/`, home-relative
`~`, unquoted Stata paths, computed paths and R raw strings are not resolved.

Columns count Unicode characters from one. Rmarkdown lines are file-relative;
inline-expression columns include their opening position. Notebook coordinates
are cell-relative, with zero-based cell indexes. Clone token spans are zero-based,
end-exclusive unions of all matching windows. A union span need not have one
partner spanning its entire length. Clone family or pair counts are not reported.

Unattributed notebook/literate failures are shown in the unit ledger and prevent
complete claims for known language profiles in the same deposit. A deposit with
only unattributed source cannot enter a language distribution; coverage tables
retain it. Environment metrics refer to the recovered manifest tables, independently
of source exclusions. Stata dependency declaration/lock/bundling metrics are
unsupported by these upstream tables, not zero.

The diagnostic audit inspected excerpts from 30 files per language followed by
30 disjoint files per language from the 100-deposit pilot. This is narrower than
a whole-file hand annotation: it cannot estimate precision, recall, authorship,
or instrument validity. Short nonfinding excerpts cannot validate absence of a
problem elsewhere. Large bundled-code deposits dominate some strata. Strata with
insufficient files are filled from the remaining deterministic ordering. See
`docs/validation.md` and the retained labels. No population-accuracy claim is made.

Code-line denominators count line occurrences within extracted source units.
Separate inline R expressions on one document line therefore contribute separately;
notebook cells have separate coordinate spaces. Token equality uses full packed
integer-token windows as dictionary keys; hash collisions still require key
equality, rather than being accepted as clone evidence.
