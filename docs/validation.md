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

## Reproducibility

`make check` and `make ci-docker` are the local checks. The pipeline records source,
input-table, instrument and specification hashes. Reports verify table hashes and
the dictionary hash, reconcile output row counts, check metric key uniqueness and
bound clone proportions. Rerunning assessment verifies cached source hashes.

The completed run on 2026-10-04 has fingerprint
`1d32aa37dbabbf8cb0ce994c9f1c56be8b295ddc0909678d325a38eab1db40c6`.
It assessed 13,982 deposits and retained all 447,257 in-frame inventory rows in
the ledger. Outputs contain 340,314 source units, 1,114,146 metric rows,
6,193,896 findings and 7,231,274 clone-span rows. These are output records,
not counts of defects or independent refactoring opportunities. Completion
checks reconciled the inventory, deposit caches and output row counts, verified
every output hash, and confirmed that input, upstream, instrument, specification
and runtime hashes still matched the starting contract.

All 48 tests passed locally on Python 3.13.2 and in standard Docker images on
Python 3.11 and 3.14; Black, isort and flake8 also passed in each environment.
The current 100-deposit pilot reproduced all five Parquet output hashes on rerun.
The full run was performed once; pilot determinism does not establish that every
full-frame source has been independently reviewed.

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
