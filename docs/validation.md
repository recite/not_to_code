# Validation record

This is a tested exploratory measurement instrument. No benchmark establishes a
single latent code-quality score, maintenance effort, scientific correctness, or
population precision/recall.

## Automated checks

The test suite exercises actual measurements and output behavior:

- comments/presentation-whitespace invariance in all three languages;
- clone self-overlap rejection, original-and-copy union coverage, short-file
  denominators, within-file cells, boundaries and hash-collision verification;
- renaming-only structural matches and adding a duplicate;
- nested control/routine structure, Stata continuations, delimiters and macros;
- malformed input, ambiguous container language, decoding and hash mismatches;
- Python docstring spans, legacy syntax, notebook magics inside strings;
- filesystem-call context versus nonpath arguments, R regex escaping;
- end-to-end CLI output, deterministic repeated/parallel runs and changed-input
  refusal, all using a synthetic source corpus.

The independent reviewer additionally compared clone coverage with a brute-force
reference on 400 randomized examples. All within/between-file masks agreed.

## Source excerpt audit

[validation-sample.json](validation-sample.json) retains 180 file selections and
labels: 30 per language for development and 30 disjoint files per language for
follow-up. Reviewer: Codex; this is not independent human annotation. Source
hashes and relative paths permit retrieval; retained excerpts make the actual
inspection scope visible.

Selections came from the initial 100-deposit pilot in SHA-256 ordering of deposit
identifiers. Within each language and phase, unique file identifiers were ordered
by SHA-256 of `PHASE-2026-10-04:FILE_UID`. Strata were filled in this order: parsing
or structure difficulty, portability findings, uncertain eligibility, nonfindings,
formatting findings, and general source. Each targeted five files; shortages were
filled from unused files. Follow-up excluded all development identifiers. Disjointness is by file ID,
not source hash or deposit: copied content can occur in both phases. Only
plain-language files were sampled; containers were exercised by fixtures.

We reviewed the retained source excerpts and selected failure locations, **not
all lines of each file**. Large bundled-code deposits dominate some strata; many
nonfinding excerpts are only a few lines. The original strata were fixed from the
pilot and can differ from the findings after repairs. These selections diagnose
failures; they cannot estimate recall, whole-file correctness or author ownership.

Development inspection prompted these repairs:

1. Decode R string escapes before recognizing UNC-like literals. Regex strings
   had been mistaken for paths before decoding.
2. Withhold entire Stata units containing embedded languages. The earlier token
   profile incorrectly treated Mata bodies as Stata source.
3. Report the opening location of unterminated ordinary Stata strings.
4. Preserve genuine Python 2 structural failures and uncertain vendor provenance.

The initial audit helper displayed three decoding failures as empty successful
sources; the assessment ledger itself correctly recorded failures. Labels retain
that distinction. Follow-up excerpts supported the narrower observed findings and
explicit withholding; no accuracy percentage is inferred.

## Independent review

The design-analysis review identified unresolved-container coverage, loose path
argument matching, Stata else-branch nesting, concatenated Python docstrings,
notebook string/magic confusion, and inline R coordinates. Each was repaired.
A second pass caught unclosed Rmarkdown chunks masked by inline expressions and
dictionary changes when reporting old results; these also received targeted fixes.
Final container checks also cover multiple inline expressions on one line and
unrecognized notebook magics.

For the first release, a separate GPT-6 Astra reviewer tested an isolated checkout
of candidate `9132d5a` and found three defects: unsupported notebook kernels could
be attributed to Python, unsupported literate engines could disappear, and Python
f-string token handling could discard literal whitespace or miss normalized
matches. Seven added regression cases failed before repair. The reviewer verified
all three repairs at commit `d25da85`, reran the original reproductions, and ran
the complete suite against both the checkout and an installed wheel. No reviewed
defect remained open. Missing notebook-language metadata now remains unattributed;
unsupported literate engines remain visible in coverage. A final regression
identified confusion between a chunk named `inline` and an inline expression;
the instrument now distinguishes them by unit identity. The same independent
reviewer reproduced and verified this repair at `4a9d252`, passing all 58 package
tests and the original three reviewer reproductions.

Release checks passed 58 tests on Python 3.13.2 locally and on Python 3.11 in
Docker, and 59 on Python 3.14 in Docker. The extra Python 3.14 case exercises
template-string literals, which that runtime adds. All three environments passed
Black, isort and flake8. At `d25da85`, the independent reviewer also passed 57
package tests and three separate reproduction tests against the wheel, with no
skipped tests. Final artifact checks cover the subsequent unit-identity repair.
GitHub CI at the repaired commit passed both supported-version jobs, including
builds and strict package-description checks. Final release metadata identifies
the publication commit and its CI run.

## Reproducibility

`make check` and `make ci-docker` are the local checks. The pipeline records source,
input-table, instrument and specification hashes. Reports verify table hashes and
the dictionary hash, reconcile output row counts, check metric key uniqueness and
bound clone proportions. Rerunning assessment verifies cached source hashes.

The completed release run on 2026-10-04 has fingerprint
`db2f4b7744186332afa3420482aca8301c7940868548a8305169a3635ca63c60`.
It assessed 13,982 deposits and retained all 447,257 in-frame inventory rows in
the ledger. Outputs contain 341,271 source units, 1,113,670 metric rows,
6,193,399 findings and 7,229,458 clone-span rows. These are output records,
not counts of defects or independent refactoring opportunities. Completion
checks reconciled the inventory, deposit caches and output row counts, verified
every output hash, and confirmed that input, upstream, instrument, specification
and runtime hashes still matched the starting contract.

The final 100-deposit pilot reproduced all five Parquet output hashes on rerun.
The final instrument's full run was performed once. Its five table hashes also
match the preceding full development run: the final chunk-label repair did not
change measurements in this recovered corpus. Pilot determinism and corpus
agreement do not establish that every source has been independently reviewed.

Full-frame results should always be read with the generated coverage tables and
the exclude-uncertain sensitivity. Excerpt review is not sufficient evidence to
rename this instrument a validated quality scale.

## Frame reconciliation

The input inventory has 447,289 files from 13,985 deposits. The pinned frame
contains 447,257 of those files from 13,982 deposits. The remaining 32 files belong
to `zenodo:3966534` (`covid-19`, 13 files), `zenodo:8408320` (`tops`, 10 files), and
`zenodo:8200032` (`eu`, 9 files), whose collection identifiers are outside that
frame. They do not enter the assessment denominator.

Source decoding uses UTF-8/BOM-aware decoding or an inventoried encoding with
confidence at least 0.7. It does not use an unconditional Latin-1 fallback.
